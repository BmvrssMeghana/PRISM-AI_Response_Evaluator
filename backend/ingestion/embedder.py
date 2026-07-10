"""
PRISM — Sentence-Transformers Embedder
Singleton wrapper around all-MiniLM-L6-v2.
Provides batched encoding for ingestion and single-query encoding for retrieval.
"""
import logging
from typing import List

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        from core.config import settings
        logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        logger.info("Embedding model loaded [OK]")
    return _model


def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    """
    Embed a list of texts and return as a list of float vectors.
    Uses batched encoding to avoid OOM on large corpora.
    """
    model = _get_model()
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=len(texts) > 200,
        normalize_embeddings=True,  # cosine similarity via dot product
        convert_to_numpy=True,
    )
    return embeddings.tolist()


def embed_query(text: str) -> List[float]:
    """Embed a single query string (used at retrieval time)."""
    return embed_texts([text])[0]
