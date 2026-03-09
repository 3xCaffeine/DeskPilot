import { useState, useEffect } from 'react'
import { screenshotUrl } from '../../api/client'
import './ScreenshotViewer.css'

export default function ScreenshotViewer({ taskId, stepNum }) {
  const [imgSrc, setImgSrc] = useState(null)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (taskId == null || stepNum == null) { setImgSrc(null); return }
    setLoaded(false)
    setError(false)
    setImgSrc(screenshotUrl(taskId, stepNum))
  }, [taskId, stepNum])

  return (
    <div className="screenshot-container">
      {!imgSrc && <p className="screenshot-placeholder">No screenshot yet.</p>}
      {imgSrc && !loaded && !error && <div className="skeleton screenshot-skel" />}
      {imgSrc && (
        <img
          key={imgSrc}
          src={imgSrc}
          alt={`Step ${stepNum}`}
          className={`screenshot-img${!loaded ? ' hidden' : ''}`}
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
        />
      )}
      {error && <p className="screenshot-placeholder">Screenshot not available.</p>}
    </div>
  )
}
