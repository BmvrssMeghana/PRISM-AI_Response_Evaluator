"""
PRISM — ChromaDB Vector Store Wrapper
Thin abstraction over ChromaDB for the reference knowledge base.
Compatible with chromadb >= 1.0.0
"""
import chromadb
from typing import List, Dict, Any
import logging

from core.config import settings

logger = logging.getLogger(__name__)

# ── Singleton client & collection ────────────────────────────────────
_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        import os
        os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    return _client


def get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        _collection = client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Public API ───────────────────────────────────────────────────────

def add_documents(
    ids: List[str],
    embeddings: List[List[float]],
    documents: List[str],
    metadatas: List[Dict[str, Any]],
    batch_size: int = 500,
) -> None:
    """Upsert documents into ChromaDB in batches."""
    collection = get_collection()
    total = len(ids)
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        collection.upsert(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )
        logger.info(f"ChromaDB upsert: {end}/{total} docs")


def query_collection(
    query_embedding: List[float],
    n_results: int = 5,
) -> Dict[str, Any]:
    """Return top-N chunks with distances and metadata."""
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],  # type: ignore
    )
    return results


def count_documents() -> int:
    """Return total number of documents in the collection."""
    return get_collection().count()


def get_collection_stats() -> Dict[str, Any]:
    """Return collection statistics for the /kb/stats endpoint."""
    collection = get_collection()
    count = collection.count()

    # Sample metadata to summarise sources
    source_counts: Dict[str, int] = {}
    if count > 0:
        try:
            sample = collection.get(
                limit=min(count, 5000),
                include=["metadatas"],  # type: ignore
            )
            for meta in (sample.get("metadatas") or []):
                src = meta.get("dataset", "unknown")
                source_counts[src] = source_counts.get(src, 0) + 1
        except Exception:
            pass  # stats are best-effort

    return {
        "total_chunks": count,
        "collection_name": settings.CHROMA_COLLECTION,
        "embedding_model": settings.EMBEDDING_MODEL,
        "source_breakdown": source_counts,
    }
