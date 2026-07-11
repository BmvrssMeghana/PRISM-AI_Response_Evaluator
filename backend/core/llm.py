"""
PRISM — Provider-Neutral LLM API Client
Provides a unified async interface to call Gemini, OpenAI, or Anthropic.
Requires at least one API key configured in .env.
"""
import json
import logging
import re
import httpx
import asyncio
from typing import Dict, Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)

# Concurrency semaphore to avoid rate-limiting issues on free tiers. Initialized lazily inside the event loop.
_sem: Optional[asyncio.Semaphore] = None

class LLMError(Exception):
    pass


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Unified entry point to call LLM providers with automatic sequential fallback.
    Tries Gemini first (if key configured), then OpenAI, then Anthropic.
    Ensures safe concurrency and retry logic to avoid rate limits (429).
    """
    global _sem
    if _sem is None:
        _sem = asyncio.Semaphore(1)

    providers = []
    if settings.GEMINI_API_KEY:
        providers.append(("gemini", _call_gemini))
    if settings.OPENAI_API_KEY:
        providers.append(("openai", _call_openai))
    if settings.ANTHROPIC_API_KEY:
        providers.append(("anthropic", _call_anthropic))

    if not providers:
        raise LLMError(
            "No LLM API keys configured. Please set GEMINI_API_KEY, "
            "OPENAI_API_KEY, or ANTHROPIC_API_KEY in your .env file."
        )

    errors = []
    # Run requests through the global semaphore to limit concurrent requests
    async with _sem:
        for name, call_func in providers:
            try:
                return await call_func(system_prompt, user_prompt, max_tokens, temperature)
            except Exception as e:
                err_msg = f"LLM Provider {name} failed: {e}"
                logger.warning(err_msg)
                errors.append(err_msg)

    raise LLMError(
        f"All configured LLM providers failed. Details:\n" + "\n".join(errors)
    )


def _extract_json(text: str) -> Dict[str, Any]:
    """Helper to find and parse JSON block from raw model output using balanced brace counting."""
    text_clean = text.strip()
    
    # First, find the first '{'
    start_idx = text_clean.find('{')
    if start_idx == -1:
        # No JSON object found
        return {
            "score": 0.0,
            "justification": f"No JSON object found in response. Raw output: {text[:200]}...",
            "vetoed": False,
            "reason": "Missing JSON",
            "claims": [],
            "unsupported_claims": [],
            "verifications": []
        }

    candidate = ""
    count = 0
    for i in range(start_idx, len(text_clean)):
        char = text_clean[i]
        if char == '{':
            count += 1
        elif char == '}':
            count -= 1
            if count == 0:
                candidate = text_clean[start_idx:i+1]
                break
    
    if not candidate:
        candidate = text_clean[start_idx:]

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from candidate: {candidate}. Error: {e}")
        # Fallback to dictionary containing error to avoid crashing orchestrator
        return {
            "score": 0.0,
            "justification": f"Error parsing judge response. Raw output: {text[:200]}...",
            "vetoed": False,
            "reason": "Format error",
            "claims": [],
            "unsupported_claims": [],
            "verifications": []
        }


async def _post_with_retry(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    retries: int = 3,
    delay: float = 8.0,
) -> httpx.Response:
    """Helper to execute POST requests with retries on rate limits (429)."""
    resp = None
    for attempt in range(retries):
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 429:
                sleep_time = delay * (attempt + 1)
                logger.warning(f"API rate limit hit (429). Retrying in {sleep_time}s... (Attempt {attempt+1}/{retries})")
                await asyncio.sleep(sleep_time)
                continue
            return resp
        except httpx.RequestError as e:
            if attempt == retries - 1:
                raise
            logger.warning(f"Request error: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
    return resp


# ── Provider: Gemini ──────────────────────────────────────────────────
async def _call_gemini(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    model = settings.GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={settings.GEMINI_API_KEY}"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"System Guidelines:\n{system_prompt}\n\nUser Content:\n{user_prompt}"}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        }
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await _post_with_retry(client, url, payload, delay=8.0)
        if resp.status_code != 200:
            raise LLMError(f"Gemini API returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return _extract_json(text)


# ── Provider: OpenAI ──────────────────────────────────────────────────
async def _call_openai(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    model = settings.OPENAI_MODEL
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await _post_with_retry(client, url, payload, headers=headers, delay=3.0)
        if resp.status_code != 200:
            raise LLMError(f"OpenAI API returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return _extract_json(text)


# ── Provider: Anthropic ───────────────────────────────────────────────
async def _call_anthropic(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    model = settings.ANTHROPIC_MODEL
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    payload = {
        "model": model,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": f"{user_prompt}\n\nIMPORTANT: Respond ONLY with a valid JSON block."}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=45.0) as client:
        resp = await _post_with_retry(client, url, payload, headers=headers, delay=4.0)
        if resp.status_code != 200:
            raise LLMError(f"Anthropic API returned status {resp.status_code}: {resp.text}")

        data = resp.json()
        text = data["content"][0]["text"]
        return _extract_json(text)
