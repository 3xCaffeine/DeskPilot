import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket(taskId) {
  const [steps, setSteps] = useState([])
  const [status, setStatus] = useState('connecting')
  const [finalAnswer, setFinalAnswer] = useState(null)
  const wsRef = useRef(null)
  const terminalRef = useRef(false)

  useEffect(() => {
    if (!taskId) return
    setSteps([])
    setStatus('connecting')
    setFinalAnswer(null)
    terminalRef.current = false

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/tasks/${taskId}`)
    wsRef.current = ws

    ws.onopen = () => setStatus('running')

    ws.onmessage = ({ data }) => {
      const msg = JSON.parse(data)
      if (msg.event_type === 'step') {
        setSteps(prev => [...prev, msg])
      } else {
        terminalRef.current = true
        setStatus(msg.event_type)
        if (msg.final_answer) setFinalAnswer(msg.final_answer)
        if (msg.error) setFinalAnswer(msg.error)
      }
    }

    ws.onerror = () => { terminalRef.current = true; setStatus('error') }
    ws.onclose = () => { if (!terminalRef.current) setStatus('error') }

    return () => ws.close()
  }, [taskId])

  const cancel = useCallback(() => {
    wsRef.current?.send(JSON.stringify({ action: 'cancel' }))
  }, [])

  return { steps, status, finalAnswer, cancel }
}
