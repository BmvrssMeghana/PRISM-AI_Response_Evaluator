"""
PRISM — Ingestion Pipeline Orchestrator
Runs: load → clean → chunk → embed → store in ChromaDB.

Idempotent: if ChromaDB already has ≥ INGEST_MIN_DOCS chunks, skip.
Call run_ingestion() from FastAPI startup event.
"""
import asyncio
import hashlib
import logging
from typing import List

from core.config import settings
from core.vector_store import count_documents, add_documents
from ingestion.loader import load_sources
from ingestion.cleaner import clean_records
from ingestion.chunker import chunk_records
from ingestion.embedder import embed_texts

logger = logging.getLogger(__name__)


def _make_chunk_id(text: str, meta: dict) -> str:
    """Stable ID for a chunk based on its full content and dataset source."""
    text_hash = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
    return f"{meta.get('dataset', 'unknown')}_{text_hash}"


def run_ingestion(sources: List[str] | None = None) -> None:
    """
    Synchronous ingestion pipeline (runs in a thread-pool from async context).
    Steps:
      1. Check if KB already populated (idempotent guard)
      2. Load raw records from HuggingFace
      3. Clean texts
      4. Chunk into 400-token segments
      5. Embed with all-MiniLM-L6-v2
      6. Upsert into ChromaDB
    """
    if sources is None:
        sources = [s.strip() for s in settings.INGEST_SOURCES.split(",")]

    current_count = count_documents()
    if current_count >= settings.INGEST_MIN_DOCS:
        logger.info(
            f"KB already has {current_count} chunks (≥ {settings.INGEST_MIN_DOCS}). "
            "Skipping ingestion."
        )
        return

    logger.info(f"Starting ingestion for sources: {sources}")

    # 1. Load
    raw_records = load_sources(sources)

    # 2. Clean
    clean = clean_records(raw_records)

    # 3. Chunk
    chunks = chunk_records(
        clean,
        chunk_size=settings.CHUNK_SIZE_TOKENS,
        overlap=settings.CHUNK_OVERLAP_TOKENS,
    )

    # 4. Embed (batched)
    texts = [c[0] for c in chunks]
    metas = [c[1] for c in chunks]

    logger.info(f"Embedding {len(texts)} chunks ...")
    embeddings = embed_texts(texts, batch_size=settings.EMBEDDING_BATCH_SIZE)

    # 5. Build IDs and upsert
    ids = [_make_chunk_id(t, m) for t, m in zip(texts, metas)]

    # Ensure metadata values are all strings/ints/floats/bools (ChromaDB requirement)
    sanitised_metas = []
    for m in metas:
        sanitised_metas.append({k: str(v) for k, v in m.items()})

    # Deduplicate before sending to ChromaDB to prevent DuplicateIDError
    seen_ids = set()
    unique_ids = []
    unique_embeddings = []
    unique_texts = []
    unique_metas = []

    for idx, chunk_id in enumerate(ids):
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            unique_ids.append(chunk_id)
            unique_embeddings.append(embeddings[idx])
            unique_texts.append(texts[idx])
            unique_metas.append(sanitised_metas[idx])

    logger.info(f"Deduplicated: {len(ids)} chunks -> {len(unique_ids)} unique chunks to upsert.")

    add_documents(
        ids=unique_ids,
        embeddings=unique_embeddings,
        documents=unique_texts,
        metadatas=unique_metas,
    )

    final_count = count_documents()
    logger.info(f"Ingestion complete. ChromaDB now has {final_count} chunks. [OK]")


async def run_ingestion_async(sources: List[str] | None = None) -> None:
    """Async wrapper — offloads blocking work to a thread pool."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, run_ingestion, sources)
