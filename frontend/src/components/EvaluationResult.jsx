import { useState, useEffect, useCallback } from 'react'

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

      if (onStatusChange) {
        onStatusChange(result.status)
      }

      if (result.status === 'evaluated' || result.status === 'failed') {
        setLoading(false)
        return true // Stop polling
      }
      return false // Continue polling
    } catch (err) {
      setError(err.message)
      setLoading(false)
      return true // Stop polling
    }
  }, [submissionId, onStatusChange])

  useEffect(() => {
    let active = true
    let timer

    const poll = async () => {
      if (!active) return
      const stop = await fetchResult()
      if (!stop && active) {
        timer = setTimeout(poll, 2500)
      }
    }

    setLoading(true)
    setError(null)
    setData(null)
    poll()

    return () => {
      active = false
      clearTimeout(timer)
    }
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
      <div className="card card-flat" style={{ padding: '1.5rem', borderColor: 'var(--black)' }}>
        <p style={{ color: 'var(--black)', fontSize: '0.875rem', fontWeight: 600 }}>⚠ Error loading report: {error}</p>
      </div>
    )
  }

  if (data?.status === 'failed') {
    return (
      <div className="card card-flat" style={{ padding: '2rem 1.5rem', textAlign: 'center', borderColor: 'var(--black)' }}>
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

  const getScoreClass = (score) => {
    if (score >= 8.0) return 'badge-dark'
    if (score >= 5.0) return 'badge-light'
    return 'badge-outline'
  }

  return (
    <div className="animate-in">
      <div className="section-header" style={{ marginBottom: '1.5rem' }}>
        <div className="section-label">Evaluation Results</div>
        <h2 style={{ fontWeight: 800, fontSize: '1.5rem', letterSpacing: '-0.02em' }}>PRISM Audit Report</h2>
        <p style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>
          Generated at {new Date(data.created_at).toLocaleTimeString()} · Local CPU Grounded RAG
        </p>
      </div>

      {/* ── SAFETY SENTINEL VETO ALERT ── */}
      {report.safety?.vetoed && (
        <div style={{
          background: 'var(--black)', color: 'var(--white)',
          padding: '1.25rem 1.5rem', borderRadius: 'var(--radius)',
          marginBottom: '2rem', border: '1.5px solid var(--black)',
          boxShadow: 'var(--shadow-sm)',
        }} className="animate-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.5rem' }}>
            <span style={{ fontSize: '1.3rem' }}>🚨</span>
            <span style={{ fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.85rem' }}>
              Safety Veto Triggered
            </span>
          </div>
          <p style={{ fontSize: '0.85rem', color: 'var(--gray-300)', lineHeight: '1.6' }}>
            {report.safety.reason}
          </p>
        </div>
      )}

      {/* ── DIMENSIONAL SCORES ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '2.5rem' }}>
        {/* Relevance */}
        <div className="card card-flat card-sm" style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Relevance</span>
            <span className={`badge ${getScoreClass(report.relevance.score)}`}>{report.relevance.score.toFixed(1)} / 10</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--gray-600)', lineHeight: '1.5' }}>{report.relevance.justification}</p>
        </div>

        {/* Accuracy */}
        <div className="card card-flat card-sm" style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Factual Accuracy</span>
            <span className={`badge ${getScoreClass(report.accuracy.score)}`}>{report.accuracy.score.toFixed(1)} / 10</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--gray-600)', lineHeight: '1.5' }}>{report.accuracy.justification}</p>
        </div>

        {/* Hallucination */}
        <div className="card card-flat card-sm" style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Grounding (Anti-Hallucination)</span>
            <span className={`badge ${getScoreClass(report.hallucination.score)}`}>{report.hallucination.score.toFixed(1)} / 10</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--gray-600)', lineHeight: '1.5' }}>{report.hallucination.justification}</p>
        </div>

        {/* Confidence Calibration */}
        <div className="card card-flat card-sm" style={{ padding: '1rem 1.25rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
            <span style={{ fontWeight: 700, fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Confidence Calibration</span>
            <span className={`badge ${getScoreClass(report.confidence.score)}`}>{report.confidence.score.toFixed(1)} / 10</span>
          </div>
          <p style={{ fontSize: '0.82rem', color: 'var(--gray-600)', lineHeight: '1.5' }}>{report.confidence.justification}</p>
        </div>
      </div>

      {/* ── CLAIMS VERIFICATION DETAIL ── */}
      {report.accuracy.verifications && report.accuracy.verifications.length > 0 && (
        <div style={{ marginBottom: '2.5rem' }}>
          <h3 style={{ fontWeight: 800, fontSize: '1.1rem', marginBottom: '1rem', letterSpacing: '-0.01em' }}>Factual Claim Verification</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {report.accuracy.verifications.map((v, i) => (
              <div key={i} style={{ border: '1px solid var(--gray-200)', borderRadius: 'var(--radius)', padding: '1rem', background: 'var(--gray-50)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem', color: 'var(--black)' }}>Claim #{i+1}: "{v.claim}"</span>
                  <span className={`badge ${v.status === 'supported' ? 'badge-dark' : 'badge-outline'}`} style={{ fontSize: '0.65rem' }}>
                    {v.status}
                  </span>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--gray-600)', fontStyle: 'italic', borderLeft: '2px solid var(--black)', paddingLeft: '0.75rem', marginTop: '0.5rem' }}>
                  <strong>Source Evidence:</strong> {v.evidence}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── UNSUPPORTED CLAIMS LIST ── */}
      {report.hallucination.unsupported_claims && report.hallucination.unsupported_claims.length > 0 && (
        <div style={{ marginBottom: '2rem' }}>
          <h3 style={{ fontWeight: 800, fontSize: '1.1rem', marginBottom: '0.75rem', letterSpacing: '-0.01em' }}>Grounding Failures (Hallucinations)</h3>
          <p style={{ fontSize: '0.78rem', color: 'var(--gray-500)', marginBottom: '0.75rem' }}>
            The following claims were stated in the response but have no supporting facts in reference documents.
          </p>
          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.82rem', color: 'var(--black)', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {report.hallucination.unsupported_claims.map((claim, idx) => (
              <li key={idx} style={{ lineHeight: '1.5' }}>{claim}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
