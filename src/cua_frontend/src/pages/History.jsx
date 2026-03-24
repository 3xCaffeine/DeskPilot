import { useState, useEffect } from 'react'
import { apiGet } from '../api/client'
import RunCard from '../components/RunCard/RunCard'
import './History.css'

const SORT_FNS = {
  newest:  (a, b) => new Date(b.created_at) - new Date(a.created_at),
  oldest:  (a, b) => new Date(a.created_at) - new Date(b.created_at),
  status:  (a, b) => a.status.localeCompare(b.status),
}

export default function History() {
  const [runs, setRuns] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState('newest')

  function loadRuns() {
    setLoading(true)
    setError(null)
    apiGet('/tasks')
      .then(setRuns)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadRuns()
  }, [])

  const filtered = runs
    .filter(r => r.goal.toLowerCase().includes(search.toLowerCase()))
    .sort(SORT_FNS[sort])

  return (
    <div className="history-page">
      <div className="history-toolbar">
        <h2 className="history-title">Run History</h2>
        <div className="history-controls">
          <input
            className="input history-search"
            placeholder="Search tasks…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select
            className="select history-sort"
            value={sort}
            onChange={e => setSort(e.target.value)}
          >
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
            <option value="status">Status</option>
          </select>
        </div>
      </div>

      {loading && (
        <div className="history-grid">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="run-card-skeleton">
              <div className="skeleton" style={{ width: '40%', height: 16 }} />
              <div className="skeleton" style={{ width: '90%', height: 12, marginTop: 8 }} />
              <div className="skeleton" style={{ width: '60%', height: 12, marginTop: 4 }} />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="history-error surface-card animate-slide-up">
          <p>Failed to load: {error}</p>
          <button className="btn btn-secondary" onClick={loadRuns}>Retry</button>
        </div>
      )}

      {!loading && !error && filtered.length === 0 && (
        <div className="history-empty">
          {search ? `No runs match "${search}"` : 'No runs yet. Start a task from the Dashboard!'}
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="history-grid">
          {filtered.map(run => <RunCard key={run.task_id} run={run} />)}
        </div>
      )}
    </div>
  )
}
