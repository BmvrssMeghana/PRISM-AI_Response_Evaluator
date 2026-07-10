"""
PRISM — Text Cleaner
Normalises raw text before chunking:
  - Strip HTML tags and markdown artefacts
  - Normalise Unicode to NFC
  - Collapse whitespace
  - Remove empty strings and very short passages (< 30 chars)
  - Deduplicate exact-match passages
"""
import re
import unicodedata
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# Patterns compiled once
_HTML_TAG = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def _clean_text(text: str) -> str:
    # Remove HTML tags
    text = _HTML_TAG.sub(" ", text)
    # Normalise unicode (NFC)
    text = unicodedata.normalize("NFC", text)
    # Replace tabs / carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    # Collapse multiple spaces
    text = _MULTI_SPACE.sub(" ", text)
    # Collapse 3+ newlines to 2
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def clean_records(
    records: List[Tuple[str, Dict[str, Any]]],
    min_length: int = 30,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Apply cleaning to every record; drop empty/duplicate texts.
    Returns cleaned (text, metadata) list.
    """
    seen: set = set()
    cleaned: List[Tuple[str, Dict[str, Any]]] = []

    for text, meta in records:
        text = _clean_text(text)
        if len(text) < min_length:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append((text, meta))

    dropped = len(records) - len(cleaned)
    logger.info(f"Cleaner: {len(cleaned)} kept, {dropped} dropped (short/duplicate)")
    return cleaned
