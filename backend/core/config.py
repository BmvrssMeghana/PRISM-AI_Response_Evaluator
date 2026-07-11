"""
PRISM — Core Configuration
All settings are pulled from environment variables (with safe defaults for dev).
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Settings(BaseSettings):
    # ── Application ─────────────────────────────────────────────────
    APP_NAME: str = "PRISM"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database (PostgreSQL — local) ────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:root@localhost:5432/prism_db"

    # ── Vector Store (ChromaDB) ──────────────────────────────────────
    CHROMA_PERSIST_DIR: str = os.path.join(BASE_DIR, "chroma_data")
    CHROMA_COLLECTION: str = "prism_kb"

    # ── Embeddings ───────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_BATCH_SIZE: int = 64

    # ── Chunking ─────────────────────────────────────────────────────
    CHUNK_SIZE_TOKENS: int = 400
    CHUNK_OVERLAP_TOKENS: int = 50

    # ── Retrieval ────────────────────────────────────────────────────
    RETRIEVAL_TOP_K: int = 5

    # ── Ingestion ────────────────────────────────────────────────────
    INGEST_SOURCES: str = "truthfulqa,squad"
    # Min docs in ChromaDB before skipping re-ingestion
    INGEST_MIN_DOCS: int = 1000

    # ── LLM Configuration ────────────────────────────────────────────
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ANTHROPIC_API_KEY: str | None = None

    GEMINI_MODEL: str = "gemini-3.5-flash"
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_MODEL: str = "claude-3-5-haiku-20241022"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
