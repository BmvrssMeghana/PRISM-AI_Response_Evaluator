import { useState, useEffect, useCallback } from 'react'

export default function KBStats() {
  const [stats, setStats] = useState(null)
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      const [statsRes, statusRes] = await Promise.all([
        fetch('/api/kb/stats'),
        fetch('/api/kb/status'),
      ])
      const s = await statsRes.json()
      const st = await statusRes.json()
      setStats(s)
      setStatus(st)
    } catch {
      // silently fail — bar is decorative
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchStats()
    const interval = setInterval(fetchStats, 30000)
    return () => clearInterval(interval)
  }, [fetchStats])

  const dotClass = loading ? 'loading' : status?.ready ? 'ready' : 'loading'

  return (
    <div className="kb-stats-bar">
      <div className="container">
        <div className="kb-stats-inner">
          <div className="kb-stat-item">
            <span className={`kb-status-dot ${dotClass}`} />
            <span>
              Knowledge Base:&nbsp;
              <strong>
                {loading ? 'Loading…'
                  : status?.ready ? 'Ready'
                  : `Ingesting (${(status?.chunk_count || 0).toLocaleString()} chunks so far…)`}
              </strong>
            </span>
          </div>

          {stats && stats.total_chunks > 0 && (
            <>
              <div className="kb-stat-dot" />
              <div className="kb-stat-item">
                <span>Chunks: <strong>{stats.total_chunks.toLocaleString()}</strong></span>
              </div>
              <div className="kb-stat-dot" />
              {stats.source_breakdown && Object.entries(stats.source_breakdown).map(([src, count]) => (
                <div className="kb-stat-item" key={src}>
                  <span>{src.toUpperCase()}: <strong>{count.toLocaleString()}</strong></span>
                </div>
              ))}
              <div className="kb-stat-dot" />
              <div className="kb-stat-item">
                <span>Model: <strong>all-MiniLM-L6-v2</strong></span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
