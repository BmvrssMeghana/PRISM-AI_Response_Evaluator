import { useState, useEffect, useCallback } from 'react'
import { ToastProvider } from './components/Toast.jsx'
import KBStats from './components/KBStats.jsx'
import SubmissionForm from './components/SubmissionForm.jsx'
import RetrievalPreview from './components/RetrievalPreview.jsx'

/* ── Recent Submission Row ── */
function SubmissionRow({ item, onClick }) {
  const date = new Date(item.created_at)
  const timeStr = date.toLocaleString('en-IN', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit'
  })
  return (
    <div className="submission-row" onClick={() => onClick(item)} tabIndex={0} role="button"
      onKeyDown={e => e.key === 'Enter' && onClick(item)}>
      <span className="submission-question">{item.question}</span>
      <div className="submission-meta">
        {item.has_reference && <span className="badge badge-light">REF</span>}
        {item.has_document && <span className="badge badge-light">DOC</span>}
        <span className="badge badge-dark">{item.status}</span>
        <span className="submission-time">{timeStr}</span>
      </div>
    </div>
  )
}

/* ── Main App ── */
export default function App() {
  const [lastSubmission, setLastSubmission] = useState(null)
  const [lastQuestion, setLastQuestion] = useState(null)
  const [submissions, setSubmissions] = useState([])
  const [subLoading, setSubLoading] = useState(false)
  const [activeTab, setActiveTab] = useState('submit') // 'submit' | 'history'

  const fetchSubmissions = useCallback(async () => {
    setSubLoading(true)
    try {
      const res = await fetch('/api/submissions?limit=20')
      const data = await res.json()
      setSubmissions(data.items || [])
    } catch {
      // silently fail
    } finally {
      setSubLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'history') fetchSubmissions()
  }, [activeTab, fetchSubmissions])

  const handleSuccess = (data, question) => {
    setLastSubmission(data)
    setLastQuestion(question)
    // Refresh if history tab is open
    if (activeTab === 'history') fetchSubmissions()
  }

  return (
    <ToastProvider>
      <div className="page-wrapper">

        {/* ── Header ── */}
        <header className="site-header">
          <div className="container">
            <div className="header-inner">
              <div className="logo">
                <div className="logo-mark">P</div>
                <span className="logo-text">PRISM</span>
                <span className="logo-tagline">AI Response Evaluator</span>
              </div>
              <nav style={{ display: 'flex', gap: '0.25rem' }}>
                <button
                  id="nav-submit"
                  className={`btn btn-ghost${activeTab === 'submit' ? ' btn-outline' : ''}`}
                  style={{ fontSize: '0.8rem' }}
                  onClick={() => setActiveTab('submit')}
                >
                  Evaluate
                </button>
                <button
                  id="nav-history"
                  className={`btn btn-ghost${activeTab === 'history' ? ' btn-outline' : ''}`}
                  style={{ fontSize: '0.8rem' }}
                  onClick={() => setActiveTab('history')}
                >
                  History
                </button>
              </nav>
            </div>
          </div>
        </header>

        {/* ── KB Stats Bar ── */}
        <KBStats />

        {/* ── Main ── */}
        <main className="main-content">
          <div className="container">

            {activeTab === 'submit' && (
              <>
                {/* Page Header */}
                <div className="section-header animate-in" style={{ marginBottom: '2.5rem' }}>
                  <div className="section-label">Milestone 1 — Evaluation Input Module</div>
                  <h1 className="section-title" style={{ fontSize: 'clamp(1.6rem, 4vw, 2.25rem)' }}>
                    Submit an AI Response
                  </h1>
                  <p className="section-desc">
                    Provide a question and the AI-generated answer you want to evaluate.
                    An optional reference answer or document grounds the evidence-based scoring.
                  </p>
                </div>

                <div className="two-col">
                  {/* Left — Form */}
                  <div className="animate-in animate-in-delay-1">
                    <div className="card">
                      {/* Success panel */}
                      {lastSubmission && (
                        <div className="success-panel" style={{ marginBottom: '1.75rem' }}>
                          <span className="success-icon">✓</span>
                          <div>
                            <div className="success-title">Submission saved — status: pending</div>
                            <div className="success-id">ID: {lastSubmission.id}</div>
                            {lastSubmission.has_document && (
                              <div style={{ fontSize: '0.75rem', color: 'var(--gray-400)', marginTop: '0.2rem' }}>
                                Document: {lastSubmission.document_filename} ({lastSubmission.document_chars.toLocaleString()} chars extracted)
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      <SubmissionForm onSuccess={handleSuccess} />
                    </div>
                  </div>

                  {/* Right — Retrieval Preview */}
                  <div className="animate-in animate-in-delay-2">
                    {lastQuestion ? (
                      <div className="card">
                        <RetrievalPreview question={lastQuestion} submissionId={lastSubmission?.id} />
                      </div>
                    ) : (
                      <div className="card card-flat" style={{ padding: '2.5rem 2rem', textAlign: 'center' }}>
                        <div style={{ fontSize: '2.5rem', marginBottom: '1rem', opacity: 0.35 }}>🔍</div>
                        <h3 style={{ fontWeight: 700, marginBottom: '0.5rem', color: 'var(--gray-700)' }}>
                          Retrieval Preview
                        </h3>
                        <p style={{ fontSize: '0.875rem', color: 'var(--gray-400)' }}>
                          After you submit a question, the top-5 most relevant reference chunks
                          will appear here with similarity scores.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* How it works */}
                <div style={{ marginTop: '3.5rem' }} className="animate-in animate-in-delay-3">
                  <hr className="divider" />
                  <div className="section-label" style={{ marginBottom: '1.25rem' }}>How PRISM Works</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                    {[
                      { num: '01', title: 'Submit', desc: 'Paste any AI-generated answer with its original question.' },
                      { num: '02', title: 'Retrieve', desc: 'PRISM searches TruthfulQA + SQuAD for the most relevant reference passages.' },
                      { num: '03', title: 'Judge', desc: 'Six specialized agents score relevance, accuracy, hallucination, completeness, and confidence.' },
                      { num: '04', title: 'Verdict', desc: 'A weighted audit report grades the answer Pass / Caution / Fail with full evidence trail.' },
                    ].map(step => (
                      <div key={step.num} className="card card-flat card-sm">
                        <div style={{ fontSize: '0.7rem', fontWeight: 800, letterSpacing: '0.15em', color: 'var(--gray-400)', marginBottom: '0.5rem' }}>
                          STEP {step.num}
                        </div>
                        <div style={{ fontWeight: 700, marginBottom: '0.35rem' }}>{step.title}</div>
                        <p style={{ fontSize: '0.82rem', color: 'var(--gray-500)' }}>{step.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}

            {activeTab === 'history' && (
              <div className="animate-in">
                <div className="section-header" style={{ marginBottom: '2rem' }}>
                  <div className="section-label">Submission History</div>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                    <h2 className="section-title" style={{ marginBottom: 0 }}>Recent Evaluations</h2>
                    <button
                      id="btn-refresh-history"
                      className="btn btn-outline"
                      onClick={fetchSubmissions}
                      disabled={subLoading}
                      style={{ fontSize: '0.78rem' }}
                    >
                      {subLoading ? <><span className="spinner spinner-dark" />Refreshing</> : '↻ Refresh'}
                    </button>
                  </div>
                </div>

                {subLoading && submissions.length === 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1.5rem 0', color: 'var(--gray-500)' }}>
                    <span className="spinner spinner-dark" />
                    <span style={{ fontSize: '0.875rem' }}>Loading submissions…</span>
                  </div>
                )}

                {!subLoading && submissions.length === 0 && (
                  <div className="card card-flat" style={{ padding: '3rem 2rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2.5rem', opacity: 0.25, marginBottom: '1rem' }}>📋</div>
                    <p style={{ color: 'var(--gray-500)' }}>No submissions yet. Use the Evaluate tab to get started.</p>
                  </div>
                )}

                {submissions.length > 0 && (
                  <div className="submissions-list">
                    {submissions.map(item => (
                      <SubmissionRow key={item.id} item={item} onClick={() => {}} />
                    ))}
                  </div>
                )}
              </div>
            )}

          </div>
        </main>

        {/* ── Footer ── */}
        <footer className="site-footer">
          <div className="container">
            <div className="footer-inner">
              <span className="footer-text">
                PRISM — AI Response Evaluator · Milestone 1
              </span>
              <span className="footer-text" style={{ fontFamily: 'monospace', fontSize: '0.72rem' }}>
                FastAPI · ChromaDB · all-MiniLM-L6-v2 · PostgreSQL
              </span>
            </div>
          </div>
        </footer>

      </div>
    </ToastProvider>
  )
}
