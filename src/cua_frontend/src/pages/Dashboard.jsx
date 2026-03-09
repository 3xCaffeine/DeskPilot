import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import TaskInput from '../components/TaskInput/TaskInput'
import StepTimeline from '../components/StepTimeline/StepTimeline'
import ScreenshotViewer from '../components/ScreenshotViewer/ScreenshotViewer'
import { useWebSocket } from '../hooks/useWebSocket'
import './Dashboard.css'

const STATUS_BADGE = {
  connecting: 'badge-muted',
  running:    'badge-running',
  completed:  'badge-success',
  failed:     'badge-error',
  cancelled:  'badge-warning',
  error:      'badge-error',
}

function ExecutionView({ task, onNewTask }) {
  const { steps, status, finalAnswer, cancel } = useWebSocket(task.taskId)
  const [pinnedStep, setPinnedStep] = useState(null)

  const latestWithShot = steps.filter(s => s.screenshot_available).at(-1)?.step ?? null
  const viewStep = pinnedStep ?? latestWithShot
  const isTerminal = ['completed', 'failed', 'cancelled', 'error'].includes(status)

  return (
    <div className="execution-view">
      <div className="execution-topbar surface-card">
        <div>
          <p className="execution-goal-label">Running task</p>
          <p className="execution-goal">{task.goal}</p>
        </div>
        <div className="execution-topbar-right">
          <span className={`badge ${STATUS_BADGE[status] ?? 'badge-muted'}`}>{status}</span>
          {!isTerminal
            ? <button className="btn btn-danger" onClick={cancel}>Cancel</button>
            : <button className="btn btn-secondary" onClick={onNewTask}>New Task</button>
          }
        </div>
      </div>

      {status === 'completed' && (
        <div className="banner banner-success animate-slide-up">
          ✓ Task complete{finalAnswer ? ` — ${finalAnswer}` : ''}
        </div>
      )}
      {status === 'failed' && (
        <div className="banner banner-error animate-slide-up">
          ✗ Task failed{finalAnswer ? ` — ${finalAnswer}` : ''}
        </div>
      )}
      {status === 'cancelled' && (
        <div className="banner banner-warning animate-slide-up">⊘ Task cancelled</div>
      )}

      <div className="execution-panels">
        <div className="execution-timeline">
          <StepTimeline steps={steps} selectedStep={pinnedStep} onSelectStep={setPinnedStep} />
        </div>
        <div className="execution-screenshot">
          <ScreenshotViewer taskId={task.taskId} stepNum={viewStep} />
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { model, setModel, availableModels, maxSteps } = useOutletContext()
  const [activeTask, setActiveTask] = useState(null)

  if (activeTask) {
    return <ExecutionView task={activeTask} onNewTask={() => setActiveTask(null)} />
  }

  return (
    <div className="dashboard-input">
      <div className="dashboard-hero">
        <h1 className="dashboard-title">DeskPilot</h1>
        <p className="dashboard-subtitle">Describe a task and watch the agent execute it on the desktop.</p>
      </div>
      <TaskInput
        model={model}
        setModel={setModel}
        availableModels={availableModels}
        maxSteps={maxSteps}
        onTaskStarted={(taskId, goal) => setActiveTask({ taskId, goal })}
      />
    </div>
  )
}
