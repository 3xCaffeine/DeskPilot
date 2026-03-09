import { useEffect, useRef } from 'react'
import './StepTimeline.css'

const BADGE = {
  PRESS_KEY:        'badge-muted',
  TYPE:             'badge-muted',
  BROWSER_NAVIGATE: 'badge-info',
  BROWSER_CLICK:    'badge-info',
  BROWSER_TYPE:     'badge-info',
  BROWSER_SCROLL:   'badge-info',
  SCREENSHOT:       'badge-muted',
  WAIT:             'badge-muted',
  DONE:             'badge-success',
  FAIL:             'badge-error',
}

export default function StepTimeline({ steps, selectedStep, onSelectStep }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }, [steps.length])

  if (steps.length === 0) {
    return (
      <div className="timeline-empty">
        <div className="skeleton" style={{ width: '60%', height: 12, marginBottom: 4 }} />
        <div className="skeleton" style={{ width: '40%', height: 12 }} />
        <p>Waiting for first step…</p>
      </div>
    )
  }

  return (
    <div className="step-timeline">
      {steps.map((step, idx) => (
        <div
          key={idx}
          className={`step-card animate-slide-up${selectedStep === step.step ? ' selected' : ''}${step.screenshot_available ? ' clickable' : ''}`}
          onClick={() => step.screenshot_available && onSelectStep(step.step)}
        >
          <div className="step-num">{step.step ?? idx + 1}</div>
          <div className="step-body">
            <div className="step-header">
              <span className={`badge ${BADGE[step.action_type] ?? 'badge-muted'}`}>
                {step.action_type}
              </span>
              <span className={`step-result ${step.result_ok ? 'ok' : 'err'}`}>
                {step.result_ok ? '✓' : '✗'}
              </span>
            </div>
            <p className="step-detail">{step.action_detail}</p>
            {step.error && <p className="step-error">{step.error}</p>}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
