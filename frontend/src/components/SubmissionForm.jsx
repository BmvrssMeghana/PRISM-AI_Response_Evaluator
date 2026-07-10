import { useState, useCallback } from 'react'
import { useToast } from './Toast.jsx'

const API = '' // proxied via Vite

const MAX_Q = 5000
const MAX_R = 10000
const MAX_REF = 8000

function CharCounter({ value, max }) {
  const pct = value.length / max
  const cls = pct > 1 ? 'over' : pct > 0.85 ? 'warn' : ''
  return (
    <div className={`char-counter ${cls}`}>
      {value.length.toLocaleString()} / {max.toLocaleString()}
    </div>
  )
}

export default function SubmissionForm({ onSuccess }) {
  const { addToast } = useToast()

  const [question, setQuestion] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [refTab, setRefTab] = useState('text') // 'text' | 'file'
  const [refAnswer, setRefAnswer] = useState('')
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [fieldErrors, setFieldErrors] = useState({})

  const validate = () => {
    const errs = {}
    if (!question.trim()) errs.question = 'Question is required'
    else if (question.length > MAX_Q) errs.question = `Must be ≤ ${MAX_Q} characters`
    if (!aiResponse.trim()) errs.aiResponse = 'AI response is required'
    else if (aiResponse.length > MAX_R) errs.aiResponse = `Must be ≤ ${MAX_R} characters`
    if (refAnswer && refAnswer.length > MAX_REF) errs.refAnswer = `Must be ≤ ${MAX_REF} characters`
    return errs
  }

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }, [])

  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f) setFile(f)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) {
      setFieldErrors(errs)
      return
    }
    setFieldErrors({})
    setLoading(true)

    const fd = new FormData()
    fd.append('question', question.trim())
    fd.append('ai_response', aiResponse.trim())
    if (refTab === 'text' && refAnswer.trim()) {
      fd.append('reference_answer', refAnswer.trim())
    }
    if (refTab === 'file' && file) {
      fd.append('file', file)
    }

    try {
      const res = await fetch(`${API}/api/submit`, { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Submission failed')

      addToast('Submission saved successfully', 'success')
      onSuccess(data, question.trim())

      // Reset form
      setQuestion('')
      setAiResponse('')
      setRefAnswer('')
      setFile(null)
    } catch (err) {
      addToast(err.message || 'Network error', 'error')
    } finally {
      setLoading(false)
    }
  }

  const fmtBytes = (b) => {
    if (!b) return ''
    if (b < 1024) return `${b} B`
    if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
    return `${(b / 1024 / 1024).toFixed(1)} MB`
  }

  return (
    <form onSubmit={handleSubmit} noValidate id="evaluation-form">

      {/* ── Question ── */}
      <div className="form-group">
        <label className="form-label" htmlFor="field-question">
          Question <span className="badge-required">Required</span>
        </label>
        <p className="form-hint">The original question posed to the AI system</p>
        <textarea
          id="field-question"
          className={`form-control${fieldErrors.question ? ' error' : ''}`}
          rows={4}
          placeholder="e.g. What causes type 2 diabetes?"
          value={question}
          onChange={e => setQuestion(e.target.value)}
          maxLength={MAX_Q + 50}
        />
        <CharCounter value={question} max={MAX_Q} />
        {fieldErrors.question && <p className="error-msg">⚠ {fieldErrors.question}</p>}
      </div>

      {/* ── AI Response ── */}
      <div className="form-group">
        <label className="form-label" htmlFor="field-response">
          AI-Generated Response <span className="badge-required">Required</span>
        </label>
        <p className="form-hint">The full response text produced by the AI system to evaluate</p>
        <textarea
          id="field-response"
          className={`form-control${fieldErrors.aiResponse ? ' error' : ''}`}
          rows={7}
          placeholder="Paste the AI response here…"
          value={aiResponse}
          onChange={e => setAiResponse(e.target.value)}
          maxLength={MAX_R + 50}
        />
        <CharCounter value={aiResponse} max={MAX_R} />
        {fieldErrors.aiResponse && <p className="error-msg">⚠ {fieldErrors.aiResponse}</p>}
      </div>

      {/* ── Optional Reference ── */}
      <div className="form-group" style={{ marginBottom: '2rem' }}>
        <label className="form-label">
          Reference Source <span className="badge-optional">Optional</span>
        </label>
        <p className="form-hint">Provide a ground-truth answer or upload a reference document (PDF / TXT)</p>

        <div className="tab-group" style={{ marginTop: '0.75rem' }}>
          <button
            type="button"
            id="tab-text"
            className={`tab-btn${refTab === 'text' ? ' active' : ''}`}
            onClick={() => setRefTab('text')}
          >
            Text Answer
          </button>
          <button
            type="button"
            id="tab-file"
            className={`tab-btn${refTab === 'file' ? ' active' : ''}`}
            onClick={() => setRefTab('file')}
          >
            Upload Document
          </button>
        </div>

        {refTab === 'text' ? (
          <>
            <textarea
              id="field-reference"
              className={`form-control${fieldErrors.refAnswer ? ' error' : ''}`}
              rows={4}
              placeholder="Enter the correct / reference answer…"
              value={refAnswer}
              onChange={e => setRefAnswer(e.target.value)}
              maxLength={MAX_REF + 50}
            />
            <CharCounter value={refAnswer} max={MAX_REF} />
            {fieldErrors.refAnswer && <p className="error-msg">⚠ {fieldErrors.refAnswer}</p>}
          </>
        ) : (
          <>
            <div
              className={`upload-zone${dragOver ? ' drag-over' : ''}`}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
            >
              <input
                type="file"
                id="field-file"
                accept=".pdf,.txt,.md"
                onChange={handleFileChange}
              />
              <span className="upload-icon">📄</span>
              <p className="upload-text">Drop file here or click to browse</p>
              <p className="upload-hint">PDF, TXT, or MD — max 10 MB</p>
            </div>
            {file && (
              <div className="upload-file-selected">
                <span style={{ fontSize: '1.1rem' }}>📎</span>
                <span className="upload-file-name">{file.name}</span>
                <span className="upload-file-size">{fmtBytes(file.size)}</span>
                <button
                  type="button"
                  className="btn-remove-file"
                  onClick={() => setFile(null)}
                  aria-label="Remove file"
                >✕</button>
              </div>
            )}
          </>
        )}
      </div>

      {/* ── Submit ── */}
      <button
        type="submit"
        id="btn-submit"
        className="btn btn-primary btn-lg w-full"
        disabled={loading}
      >
        {loading ? (
          <><span className="spinner" />Submitting…</>
        ) : (
          <>Submit for Evaluation →</>
        )}
      </button>
    </form>
  )
}
