"""
PRISM — Provider-Neutral LLM API Client
Provides a unified async interface to call Gemini, OpenAI, or Anthropic.
Requires at least one API key configured in .env.
"""
import json
import logging
import re
import httpx
from typing import Dict, Any, Optional

from core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 1500,
    temperature: float = 0.1,
) -> Dict[str, Any]:
    """
    Unified entry point to call LLM providers.
    Uses sequential fallback: tries Gemini first (if key configured),
    then OpenAI, then Anthropic. If one fails, falls back to the next.
    """
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
    """Helper to find and parse JSON block from raw model output."""
    text_clean = text.strip()
    # Try finding markdown code block e.g. ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text_clean, re.DOTALL)
    if match:
        candidate = match.group(1)
    else:
        # Try raw braces search
        match_raw = re.search(r"(\{.*\})", text_clean, re.DOTALL)
        candidate = match_raw.group(1) if match_raw else text_clean

    try:
        return json.loads(candidate)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from text: {text_clean}. Error: {e}")
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
        try:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise LLMError(f"Gemini API returned status {resp.status_code}: {resp.text}")

            data = resp.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            return _extract_json(text)
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"Gemini API call failed: {e}") from e


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
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise LLMError(f"OpenAI API returned status {resp.status_code}: {resp.text}")

            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            return _extract_json(text)
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"OpenAI API call failed: {e}") from e


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
        try:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                raise LLMError(f"Anthropic API returned status {resp.status_code}: {resp.text}")

            data = resp.json()
            text = data["content"][0]["text"]
            return _extract_json(text)
        except Exception as e:
            if isinstance(e, LLMError):
                raise
            raise LLMError(f"Anthropic API call failed: {e}") from e
