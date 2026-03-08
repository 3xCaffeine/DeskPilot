import { useParams, Link } from 'react-router-dom'

export default function RunDetail() {
  const { runId } = useParams()
  return (
    <div>
      <Link to="/history">← Back to History</Link>
      <p>Run Detail: {runId} — Phase 6</p>
    </div>
  )
}
