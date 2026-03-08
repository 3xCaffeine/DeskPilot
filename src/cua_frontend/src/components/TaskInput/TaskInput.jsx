import { useState, useRef } from 'react'
import { apiGet, apiPost } from '../../api/client'
import './TaskInput.css'

export default function TaskInput({ model, maxSteps, onTaskStarted }) {
  const [goal, setGoal] = useState('')
  const [steps, setSteps] = useState(maxSteps ?? 10)
  const [loadingRandom, setLoadingRandom] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const textareaRef = useRef(null)

  async function handleRandom() {
    setLoadingRandom(true)
    try {
      const data = await apiGet('/random-task')
      setGoal('')
      const text = data.task
      for (let i = 1; i <= text.length; i++) {
        await new Promise(r => setTimeout(r, 22))
        setGoal(text.slice(0, i))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoadingRandom(false)
      textareaRef.current?.focus()
    }
  }

  async function handleSubmit() {
    if (!goal.trim()) return
    setSubmitting(true)
    try {
      const data = await apiPost('/tasks', { goal: goal.trim(), model, max_steps: steps })
      onTaskStarted(data.task_id, goal.trim())
    } catch (e) {
      console.error(e)
      setSubmitting(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit()
  }

  return (
    <div className="task-input glass-card">
      <div className="task-input-header">
        <h3>What should DeskPilot do?</h3>
        <span className="task-input-hint">Ctrl+Enter to run</span>
      </div>

      <textarea
        ref={textareaRef}
        className="textarea task-textarea"
        rows={5}
        placeholder="e.g. Open Chrome and search for React tutorials..."
        value={goal}
        onChange={e => setGoal(e.target.value)}
        onKeyDown={handleKeyDown}
      />

      <div className="task-input-footer">
        <div className="task-input-steps">
          <label className="steps-label">
            Max steps <span className="steps-value">{steps}</span>
          </label>
          <input
            type="range"
            min={1} max={50}
            value={steps}
            onChange={e => setSteps(Number(e.target.value))}
            className="steps-slider"
          />
        </div>

        <div className="task-input-actions">
          <button
            className={`btn btn-secondary${loadingRandom ? ' loading' : ''}`}
            onClick={handleRandom}
            disabled={loadingRandom || submitting}
          >
            <span className={loadingRandom ? 'spin' : ''}>🎲</span>
            Random
          </button>

          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={!goal.trim() || submitting}
          >
            {submitting ? <span className="spin">⏳</span> : '🚀'}
            Run Task
          </button>
        </div>
      </div>
    </div>
  )
}
