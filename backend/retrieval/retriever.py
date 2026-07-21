"""
PRISM — Semantic Retriever
Embeds a question and fetches top-K chunks from ChromaDB.
Filters out low-similarity noise using strict cosine thresholding.
"""
import logging
from typing import List, Dict, Any

from core.vector_store import query_collection
from ingestion.embedder import embed_query

logger = logging.getLogger(__name__)

# Minimum cosine similarity threshold (1.0 - dist) for a passage to be considered relevant evidence.
MIN_SIMILARITY_THRESHOLD = 0.5


def retrieve(question: str, k: int = 5, min_threshold: float = MIN_SIMILARITY_THRESHOLD) -> List[Dict[str, Any]]:
    """
    Embed `question`, query ChromaDB, calculate TRUE cosine similarity,
    and return ONLY top-K results that pass the relevance threshold.

    Each result dict:
      - text: str
      - score: float (cosine similarity, 0–1; higher = more relevant)
      - source: str
      - dataset: str
      - metadata: dict
    """
    embedding = embed_query(question)
    # Query up to 10 candidates to ensure we can get k high-quality matches
    raw = query_collection(query_embedding=embedding, n_results=max(k * 2, 10))

    results = []
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        # ChromaDB hnsw:space cosine distance: dist = 1.0 - cos_sim
        # TRUE Cosine Similarity: 1.0 - dist
        similarity = round(max(0.0, 1.0 - float(dist)), 4)

        # Reject irrelevant noise below minimum similarity threshold
        if similarity < min_threshold:
            logger.info(f"Filtered out low-relevance chunk (score={similarity} < {min_threshold}): '{doc[:50]}...'")
            continue

        results.append({
            "text": doc,
            "score": similarity,
            "source": meta.get("source", "unknown"),
            "dataset": meta.get("dataset", "unknown"),
            "metadata": meta,
        })
        if len(results) >= k:
            break

    logger.info(f"Retrieved {len(results)} relevant evidence chunks (min_score >= {min_threshold}) for question: '{question[:50]}'")
    return results
