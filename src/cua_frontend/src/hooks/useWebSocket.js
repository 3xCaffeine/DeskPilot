import { useState, useEffect, useRef, useCallback } from 'react'

export function useWebSocket(taskId) {
  const [steps, setSteps] = useState([])
  const [status, setStatus] = useState('connecting')
  const [finalAnswer, setFinalAnswer] = useState(null)
  const [logs, setLogs] = useState([])
  const wsRef = useRef(null)
  const terminalRef = useRef(false)
  const cancelPendingRef = useRef(false)
  const pollTimerRef = useRef(null)

  const addLog = (level, msg) => {
    const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
    setLogs(prev => [...prev, { ts, level, msg }])
  }

  useEffect(() => {
    if (!taskId) return
    setSteps([])
    setStatus('connecting')
    setFinalAnswer(null)
    terminalRef.current = false
    cancelPendingRef.current = false
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current)

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/tasks/${taskId}`)
    wsRef.current = ws
    addLog('info', `WS connecting → /ws/tasks/${taskId}`)

    ws.onopen = () => { setStatus('running'); addLog('info', 'WS connected') }

    ws.onmessage = ({ data }) => {
      const msg = JSON.parse(data)
      if (msg.event_type === 'step') {
        addLog('step', `[step ${msg.step}] ${msg.action_type} — ${msg.action_detail}${msg.error ? ' ERROR: ' + msg.error : ''}`)
        setSteps(prev => [...prev, msg])
      } else {
        addLog(msg.event_type === 'completed' ? 'ok' : 'error',
          `${msg.event_type.toUpperCase()}${msg.final_answer ? ': ' + msg.final_answer : ''}${msg.error ? ': ' + msg.error : ''}`)
        terminalRef.current = true
        setStatus(msg.event_type)
        if (msg.final_answer) setFinalAnswer(msg.final_answer)
        if (msg.error) setFinalAnswer(msg.error)
      }
    }

    ws.onerror = (e) => { addLog('error', 'WS error'); terminalRef.current = true; setStatus('error') }
    ws.onclose = () => {
      addLog('info', 'WS closed')
      if (terminalRef.current) return
      setStatus('reconnecting')

      const TERMINAL = new Set(['completed', 'failed', 'cancelled'])
      // If cancel was pending, the agent may still be finishing — poll with retries
      const maxRetries = cancelPendingRef.current ? 15 : 1
      const interval = cancelPendingRef.current ? 1000 : 0
      let attempt = 0

      const poll = () => {
        addLog('info', attempt === 0 ? 'Polling API for final status…' : `Polling… (${attempt + 1}/${maxRetries})`)
        fetch(`/api/tasks/${taskId}`)
          .then(r => r.json())
          .then(data => {
            if (TERMINAL.has(data.status)) {
              addLog(data.status === 'completed' ? 'ok' : data.status === 'cancelled' ? 'cancelled' : 'error',
                `API status: ${data.status}`)
              terminalRef.current = true
              setStatus(data.status)
              if (data.final_answer) setFinalAnswer(data.final_answer)
              if (data.error) setFinalAnswer(data.error)
            } else if (++attempt < maxRetries) {
              pollTimerRef.current = setTimeout(poll, interval)
            } else {
              addLog('error', `Gave up polling — last status: ${data.status}`)
            }
          })
          .catch(() => { addLog('error', 'API poll failed'); setStatus('error') })
      }
      poll()
    }

    return () => {
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
      ws.close()
    }
  }, [taskId])

  const cancel = useCallback(() => {
    addLog('info', 'Cancelling task…')
    cancelPendingRef.current = true
    terminalRef.current = true
    setStatus('cancelled')
    try { wsRef.current?.send(JSON.stringify({ action: 'cancel' })) } catch {}
    try { wsRef.current?.close() } catch {}
  }, [])

  return { steps, status, finalAnswer, logs, cancel }
}
