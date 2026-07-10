# PRISM — AI Response Evaluator

**P**assage **R**etrieval and **I**ntelligent **S**coring **M**odel

An evidence-grounded AI response evaluation system. Phase 1 establishes the Evaluation Input Module and Reference Knowledge Base.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **PostgreSQL** (local, user: `postgres`, password: `root`, port: `5432`)

---

## Quick Start

### 1. Create the database

```sql
-- In psql or pgAdmin:
CREATE DATABASE prism_db;
```

### 2. Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

On first start, the backend will:
- Create the `submissions` table automatically
- Launch background ingestion of TruthfulQA + SQuAD (~5–10 min on CPU, skipped on subsequent starts)

API docs: http://localhost:8000/docs

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open: http://localhost:5173

---

## Project Structure

```
backend/
  main.py              # FastAPI app (startup, routes, CORS)
  core/
    config.py          # Settings from .env
    database.py        # PostgreSQL + SQLAlchemy async
    vector_store.py    # ChromaDB wrapper
  ingestion/
    loader.py          # HuggingFace dataset loader
    cleaner.py         # Text normalisation
    chunker.py         # 400-token chunks, 50-token overlap
    embedder.py        # all-MiniLM-L6-v2 (singleton)
    pipeline.py        # Orchestrator (idempotent)
  retrieval/
    retriever.py       # Embed query → top-K chunks
  api/routes/
    submissions.py     # POST /api/submit, GET /api/submissions
    knowledge.py       # GET /api/kb/retrieve, /api/kb/stats

frontend/
  src/
    App.jsx            # Main layout, tabs, history
    components/
      SubmissionForm.jsx    # Form with validation, char counter, file upload
      RetrievalPreview.jsx  # Expandable chunk cards with score bars
      KBStats.jsx           # Live KB status bar (polls every 30s)
      Toast.jsx             # Notification system
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/submit` | Submit question + AI response (+ optional ref/doc) |
| GET | `/api/submissions` | List submissions (paginated) |
| GET | `/api/submissions/{id}` | Get single submission |
| GET | `/api/kb/retrieve?question=...&k=5` | Semantic search over KB |
| GET | `/api/kb/stats` | KB chunk count and source breakdown |
| GET | `/api/kb/status` | Ingestion readiness check |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

---

## Technology Stack

| Layer | Choice |
|-------|--------|
| Backend | FastAPI + uvicorn |
| Database | PostgreSQL + SQLAlchemy async |
| Vector Store | ChromaDB (persisted to `./chroma_data`) |
| Embeddings | all-MiniLM-L6-v2 (384-d, CPU-local) |
| Datasets | TruthfulQA + SQuAD via Hugging Face |
| Frontend | React + Vite |
| Styling | Vanilla CSS (Raleway, black/white) |

---

## Environment Variables (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:root@localhost:5432/prism_db` | PostgreSQL connection |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `CHUNK_SIZE_TOKENS` | `400` | Chunk size in tokens |
| `CHUNK_OVERLAP_TOKENS` | `50` | Overlap between chunks |
| `RETRIEVAL_TOP_K` | `5` | Chunks returned per query |
| `INGEST_SOURCES` | `truthfulqa,squad` | Datasets to ingest |
| `INGEST_MIN_DOCS` | `1000` | Skip ingestion if KB ≥ this |
