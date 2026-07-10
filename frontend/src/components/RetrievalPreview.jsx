import { useState, useEffect } from 'react'

function ChunkCard({ chunk, index }) {
  const [open, setOpen] = useState(index === 0) // first card expanded by default

  const pct = Math.round(chunk.score * 100)
  const scoreLabel = pct >= 80 ? 'High' : pct >= 55 ? 'Medium' : 'Low'

  return (
    <div className="chunk-card animate-in" style={{ animationDelay: `${index * 0.06}s` }}>
      <div className="chunk-header" onClick={() => setOpen(o => !o)}>
        <div className="chunk-meta">
          <span className="badge badge-dark">#{index + 1}</span>
          <span className="badge badge-light">{chunk.dataset || 'unknown'}</span>
          {chunk.metadata?.type && (
            <span className="badge badge-outline">{chunk.metadata.type}</span>
          )}
        </div>

        {/* Score bar */}
        <div className="score-bar-wrap" style={{ minWidth: '140px', maxWidth: '180px' }}>
          <div className="score-bar-track">
            <div className="score-bar-fill" style={{ width: `${pct}%` }} />
          </div>
          <span className="score-value">{chunk.score.toFixed(3)}</span>
        </div>

        <span className={`chunk-toggle${open ? ' open' : ''}`}>▼</span>
      </div>

      {open && (
        <div className="chunk-body">
          {chunk.text}
          {chunk.metadata?.title && (
            <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--gray-400)', fontWeight: 600 }}>
              Source: {chunk.metadata.title}
            </div>
          )}
          {chunk.metadata?.question && (
            <div style={{ marginTop: '0.35rem', fontSize: '0.75rem', color: 'var(--gray-400)', fontWeight: 600 }}>
              Q: {chunk.metadata.question}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function RetrievalPreview({ question, submissionId }) {
  const [chunks, setChunks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!question) return
    setLoading(true)
    setError(null)

    fetch(`/api/kb/retrieve?question=${encodeURIComponent(question)}&k=5`)
      .then(r => r.json())
      .then(data => {
        if (data.detail) throw new Error(data.detail)
        setChunks(data.results || [])
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [question, submissionId])

  return (
    <div>
      <div className="section-header" style={{ marginBottom: '1.25rem' }}>
        <div className="section-label">Reference Knowledge Base</div>
        <h3 style={{ fontWeight: 800, letterSpacing: '-0.01em' }}>Retrieval Preview</h3>
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginTop: '0.25rem' }}>
          Top-5 reference chunks retrieved for this question. These will ground the judge agents.
        </p>
      </div>

      {loading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem 0', color: 'var(--gray-500)' }}>
          <span className="spinner spinner-dark" />
          <span style={{ fontSize: '0.875rem', fontWeight: 500 }}>Searching knowledge base…</span>
        </div>
      )}

      {error && (
        <div className="card card-flat" style={{ padding: '1.25rem' }}>
          <p style={{ fontSize: '0.875rem', color: 'var(--gray-600)' }}>
            {error.includes('empty') || error.includes('503')
              ? '⏳ Knowledge base is still being populated. Results will appear once ingestion completes.'
              : `⚠ ${error}`}
          </p>
        </div>
      )}

      {!loading && !error && chunks.length === 0 && (
        <div className="card card-flat" style={{ padding: '1.25rem' }}>
          <p style={{ fontSize: '0.875rem', color: 'var(--gray-500)' }}>No relevant chunks found.</p>
        </div>
      )}

      {!loading && chunks.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          {chunks.map((chunk, i) => (
            <ChunkCard key={i} chunk={chunk} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
