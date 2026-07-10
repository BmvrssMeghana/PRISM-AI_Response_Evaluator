"""
PRISM — Token-Aware Text Chunker
Splits cleaned passages into overlapping chunks using tiktoken.
  - Chunk size: 400 tokens (configurable)
  - Overlap: 50 tokens (configurable)
  - Metadata from parent record is preserved + chunk_index added
"""
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

try:
    import tiktoken
    _enc = tiktoken.get_encoding("cl100k_base")
except Exception:
    _enc = None
    logger.warning("tiktoken not available — falling back to word-based splitting")


def _tokenize(text: str) -> List[int]:
    if _enc is not None:
        return _enc.encode(text)
    # Word-based fallback
    return text.split()


def _detokenize(tokens) -> str:
    if _enc is not None:
        return _enc.decode(tokens)
    return " ".join(tokens)


def chunk_records(
    records: List[Tuple[str, Dict[str, Any]]],
    chunk_size: int = 400,
    overlap: int = 50,
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Chunk each (text, metadata) record and return a flat list of chunks.
    Each chunk gets a `chunk_index` and `total_chunks` added to metadata.
    """
    all_chunks: List[Tuple[str, Dict[str, Any]]] = []

    for text, meta in records:
        tokens = _tokenize(text)
        if len(tokens) == 0:
            continue

        if len(tokens) <= chunk_size:
            # Short enough — single chunk
            all_chunks.append((text, {**meta, "chunk_index": 0, "total_chunks": 1}))
            continue

        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = _detokenize(chunk_tokens).strip()
            if chunk_text:
                chunks.append(chunk_text)
            if end == len(tokens):
                break
            start += chunk_size - overlap

        total = len(chunks)
        for idx, chunk_text in enumerate(chunks):
            all_chunks.append((chunk_text, {**meta, "chunk_index": idx, "total_chunks": total}))

    logger.info(f"Chunker: {len(records)} records → {len(all_chunks)} chunks")
    return all_chunks
