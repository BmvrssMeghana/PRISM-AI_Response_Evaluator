"""
PRISM — Semantic Retriever
Embeds a question and fetches top-K chunks from ChromaDB.
Returns structured results ready for API responses.
"""
import logging
from typing import List, Dict, Any

from core.vector_store import query_collection
from ingestion.embedder import embed_query

logger = logging.getLogger(__name__)


def retrieve(question: str, k: int = 5) -> List[Dict[str, Any]]:
    """
    Embed `question`, query ChromaDB, and return top-K results.

    Each result dict:
      - text: str
      - score: float (cosine similarity, 0–1; higher = more relevant)
      - source: str
      - dataset: str
      - metadata: dict (all stored metadata)
    """
    embedding = embed_query(question)
    raw = query_collection(query_embedding=embedding, n_results=k)

    results = []
    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    for doc, meta, dist in zip(docs, metas, distances):
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score [0, 1]
        similarity = round(max(0.0, 1.0 - dist / 2.0), 4)
        results.append({
            "text": doc,
            "score": similarity,
            "source": meta.get("source", "unknown"),
            "dataset": meta.get("dataset", "unknown"),
            "metadata": meta,
        })

    return results
