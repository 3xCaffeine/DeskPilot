import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import TaskInput from '../components/TaskInput/TaskInput'
import './Dashboard.css'

export default function Dashboard() {
  const { model, setModel, availableModels, maxSteps } = useOutletContext()
  const [activeTask, setActiveTask] = useState(null)

  function handleTaskStarted(taskId, goal) {
    setActiveTask({ taskId, goal })
  }

  function handleNewTask() {
    setActiveTask(null)
  }

  if (activeTask) {
    return (
      <div className="dashboard-execution">
        <div className="execution-header">
          <div>
            <p className="execution-goal-label">Running task</p>
            <p className="execution-goal">{activeTask.goal}</p>
          </div>
          <button className="btn btn-ghost" onClick={handleNewTask}>✕ New Task</button>
        </div>
        <div className="execution-placeholder surface-card">
          <p>⏳ Task <code>{activeTask.taskId}</code> started.</p>
          <p className="text-muted" style={{ marginTop: 8 }}>Live view coming in Phase 5.</p>
        </div>
      </div>
    )
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
        onTaskStarted={handleTaskStarted}
      />
    </div>
  )
}
