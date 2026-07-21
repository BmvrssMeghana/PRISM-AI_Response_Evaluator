import { useState, useEffect, useCallback } from 'react'

/* ── Collapsible Section ── */
function Section({ title, badge, defaultOpen = false, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div style={{ marginBottom: '1rem', border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '0.85rem 1.1rem', background: 'var(--gray-50)', border: 'none',
          cursor: 'pointer', fontWeight: 700, fontSize: '0.88rem', letterSpacing: '0.02em',
          color: 'var(--black)', textAlign: 'left',
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span style={{ fontSize: '0.75rem', transition: 'transform 0.2s', display: 'inline-block', transform: open ? 'rotate(90deg)' : 'rotate(0deg)' }}>▶</span>
          {title}
        </span>
        {badge && <span className="badge badge-outline" style={{ fontSize: '0.68rem' }}>{badge}</span>}
      </button>
      {open && (
        <div style={{ padding: '1rem 1.1rem', background: '#fff', borderTop: '1px solid var(--gray-200)' }}>
          {children}
        </div>
      )}
    </div>
  )
}

/* ── Score Card ── */
function ScoreCard({ label, score, justification }) {
  const color = score >= 8 ? '#16a34a' : score >= 5 ? '#ca8a04' : '#dc2626'
  const bg = score >= 8 ? '#f0fdf4' : score >= 5 ? '#fefce8' : '#fef2f2'
  const border = score >= 8 ? '#bbf7d0' : score >= 5 ? '#fde68a' : '#fecaca'
  return (
    <div style={{
      border: `1.5px solid ${border}`, borderRadius: 'var(--radius)',
      padding: '1.1rem 1.25rem', background: bg,
      display: 'flex', flexDirection: 'column', gap: '0.5rem',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <span style={{ fontSize: '0.72rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--gray-600)' }}>
          {label}
        </span>
        <div style={{ textAlign: 'right' }}>
          <span style={{ fontSize: '2rem', fontWeight: 900, lineHeight: 1, color, display: 'block' }}>
            {score.toFixed(1)}
          </span>
          <span style={{ fontSize: '0.7rem', color: 'var(--gray-500)', fontWeight: 600 }}>/&nbsp;10</span>
        </div>
      </div>
      <p style={{ fontSize: '0.79rem', color: 'var(--gray-700)', lineHeight: '1.5', margin: 0 }}>
        {justification}
      </p>
    </div>
  )
}

/* ── Main Component ── */
export default function EvaluationResult({ submissionId, onStatusChange }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchResult = useCallback(async () => {
    try {
      const res = await fetch(`/api/submissions/${submissionId}`)
      if (!res.ok) throw new Error('Failed to fetch details')
      const result = await res.json()
      setData(result)
      if (onStatusChange) onStatusChange(result.status)
      if (result.status === 'evaluated' || result.status === 'failed') {
        setLoading(false)
        return true
      }
      return false
    } catch (err) {
      setError(err.message)
      setLoading(false)
      return true
    }
  }, [submissionId, onStatusChange])

  useEffect(() => {
    let active = true
    let timer
    const poll = async () => {
      if (!active) return
      const stop = await fetchResult()
      if (!stop && active) timer = setTimeout(poll, 2500)
    }
    setLoading(true)
    setError(null)
    setData(null)
    poll()
    return () => { active = false; clearTimeout(timer) }
  }, [submissionId, fetchResult])

  if (loading && (!data || data.status === 'pending')) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem 2rem', textAlign: 'center' }}>
        <span className="spinner spinner-dark" style={{ width: '32px', height: '32px', borderWidth: '3.5px', marginBottom: '1.25rem' }} />
        <h4 style={{ fontWeight: 700, marginBottom: '0.4rem' }}>Judging in Progress</h4>
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', maxWidth: '280px' }}>
          PRISM agents are extracting claims and auditing them against the Reference Knowledge Base...
        </p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card card-flat" style={{ padding: '1.5rem' }}>
        <p style={{ color: 'var(--black)', fontSize: '0.875rem', fontWeight: 600 }}>⚠ Error loading report: {error}</p>
      </div>
    )
  }

  if (data?.status === 'failed') {
    return (
      <div className="card card-flat" style={{ padding: '2rem 1.5rem', textAlign: 'center' }}>
        <span style={{ fontSize: '2rem', display: 'block', marginBottom: '0.75rem' }}>⚠</span>
        <h4 style={{ fontWeight: 800, marginBottom: '0.5rem' }}>Evaluation Failed</h4>
        <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)' }}>
          An unexpected error occurred during LLM agent analysis. Check backend logs for details.
        </p>
      </div>
    )
  }

  const report = data?.evaluation_results
  if (!report) return null

  const hasChunks = report.retrieved_passages && report.retrieved_passages.length > 0
  const hasClaims = report.accuracy?.verifications && report.accuracy.verifications.length > 0
  const hasHallucinations = report.hallucination?.unsupported_claims && report.hallucination.unsupported_claims.length > 0

  return (
    <div className="animate-in">

      {/* ── HEADER ── */}
      <div style={{ marginBottom: '1.25rem' }}>
        <div className="section-label">Evaluation Results</div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '0.5rem' }}>
          <h2 style={{ fontWeight: 800, fontSize: '1.35rem', letterSpacing: '-0.02em', margin: 0 }}>PRISM Audit Report</h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--gray-500)' }}>
            {new Date(data.created_at).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })} · RAG Grounded
          </span>
        </div>
      </div>

      {/* ── INPUT SUMMARY ── */}
      <Section title="Submitted Input" defaultOpen={true}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div>
            <div style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--gray-500)', marginBottom: '0.3rem' }}>Question</div>
            <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--black)', lineHeight: '1.5' }}>{data.question}</div>
          </div>
          <div>
            <div style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--gray-500)', marginBottom: '0.3rem' }}>AI Response</div>
            <div style={{ fontSize: '0.84rem', color: 'var(--gray-800)', lineHeight: '1.6', background: 'var(--gray-50)', padding: '0.7rem 0.9rem', borderRadius: '6px', borderLeft: '3px solid var(--black)' }}>
              {data.ai_response}
            </div>
          </div>
          {data.reference_answer && (
            <div>
              <div style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--gray-500)', marginBottom: '0.3rem' }}>Reference Answer</div>
              <div style={{ fontSize: '0.84rem', color: 'var(--gray-800)', lineHeight: '1.6', background: '#f0fdf4', padding: '0.7rem 0.9rem', borderRadius: '6px', borderLeft: '3px solid #16a34a' }}>
                {data.reference_answer}
              </div>
            </div>
          )}
          {data.document_filename && (
            <div>
              <div style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--gray-500)', marginBottom: '0.3rem' }}>Uploaded Document</div>
              <span className="badge badge-light" style={{ fontSize: '0.75rem' }}>📄 {data.document_filename}</span>
            </div>
          )}
        </div>
      </Section>

      {/* ── SAFETY ALERT ── */}
      {report.safety?.vetoed && (
        <div style={{
          background: 'var(--black)', color: 'var(--white)',
          padding: '1rem 1.25rem', borderRadius: 'var(--radius)', marginBottom: '1rem',
        }} className="animate-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.4rem' }}>
            <span>🚨</span>
            <span style={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.8rem' }}>Safety Veto Triggered</span>
          </div>
          <p style={{ fontSize: '0.83rem', color: 'var(--gray-300)', lineHeight: '1.5', margin: 0 }}>{report.safety.reason}</p>
        </div>
      )}

      {/* ── SCORE CARDS 2×2 GRID ── */}
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.68rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--gray-500)', marginBottom: '0.75rem' }}>
          Dimensional Scores
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
          <ScoreCard label="Relevance" score={report.relevance?.score ?? 0} justification={report.relevance?.justification} />
          <ScoreCard label="Factual Accuracy" score={report.accuracy?.score ?? 0} justification={report.accuracy?.justification} />
          <ScoreCard label="Anti-Hallucination" score={report.hallucination?.score ?? 0} justification={report.hallucination?.justification} />
          <ScoreCard label="Confidence Calibration" score={report.confidence?.score ?? 0} justification={report.confidence?.justification} />
        </div>
      </div>

      {/* ── RETRIEVED REFERENCE CHUNKS ── */}
      <Section
        title="Retrieved Reference Evidence"
        badge={hasChunks ? `${report.retrieved_passages.length} chunks` : 'KB gap'}
        defaultOpen={false}
      >
        {hasChunks ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {report.retrieved_passages.map((chunk, idx) => (
              <div key={idx} style={{ border: '1px solid var(--gray-200)', borderRadius: '6px', padding: '0.85rem 1rem', background: 'var(--gray-50)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem', flexWrap: 'wrap', gap: '0.4rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                    <span className="badge badge-dark" style={{ fontSize: '0.62rem' }}>Chunk #{idx + 1}</span>
                    <span style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--gray-700)' }}>
                      {chunk.source || chunk.dataset || 'Reference KB'}
                    </span>
                  </div>
                  <span className="badge badge-outline" style={{ fontSize: '0.7rem', fontWeight: 700 }}>
                    {typeof chunk.score === 'number' ? (chunk.score * 100).toFixed(1) + '%' : chunk.score} match
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--gray-800)', lineHeight: '1.55', fontFamily: 'monospace', whiteSpace: 'pre-wrap', borderLeft: '3px solid var(--black)', paddingLeft: '0.65rem' }}>
                  {chunk.text}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>📭</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.84rem', marginBottom: '0.25rem' }}>No Relevant Passages Found in Reference KB</div>
              <p style={{ fontSize: '0.79rem', color: 'var(--gray-600)', margin: 0, lineHeight: '1.55' }}>
                No chunks scored above the <strong>50% cosine similarity threshold</strong> for this question.
                This is a <strong>KB coverage gap</strong> — agents evaluated using general world knowledge instead.
              </p>
            </div>
          </div>
        )}
      </Section>

      {/* ── CLAIMS VERIFICATION ── */}
      {hasClaims && (
        <Section title="Factual Claim Verification" badge={`${report.accuracy.verifications.length} claims`} defaultOpen={false}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
            {report.accuracy.verifications.map((v, i) => (
              <div key={i} style={{ border: '1px solid var(--gray-200)', borderRadius: '6px', padding: '0.85rem 1rem', background: 'var(--gray-50)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.4rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.83rem', color: 'var(--black)', flex: 1 }}>"{v.claim}"</span>
                  <span className={`badge ${v.status === 'supported' ? 'badge-dark' : v.status === 'contradicted' ? 'badge-outline' : 'badge-light'}`} style={{ fontSize: '0.62rem', flexShrink: 0 }}>
                    {v.status}
                  </span>
                </div>
                <div style={{ fontSize: '0.76rem', color: 'var(--gray-600)', fontStyle: 'italic', borderLeft: '2px solid var(--black)', paddingLeft: '0.65rem' }}>
                  <strong>Evidence:</strong> {v.evidence}
                </div>
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── HALLUCINATION FAILURES ── */}
      {hasHallucinations && (
        <Section title="Grounding Failures (Hallucinations)" badge={`${report.hallucination.unsupported_claims.length} flagged`} defaultOpen={false}>
          <p style={{ fontSize: '0.78rem', color: 'var(--gray-500)', marginBottom: '0.65rem', marginTop: 0 }}>
            These claims were in the response but have no supporting facts in reference documents.
          </p>
          <ul style={{ paddingLeft: '1.1rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
            {report.hallucination.unsupported_claims.map((claim, idx) => (
              <li key={idx} style={{ fontSize: '0.82rem', color: 'var(--black)', lineHeight: '1.5' }}>{claim}</li>
            ))}
          </ul>
        </Section>
      )}

    </div>
  )
}
