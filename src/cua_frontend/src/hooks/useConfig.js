import { useState, useEffect } from 'react'
import { apiGet, apiPut } from '../api/client'

export function useConfig() {
  const [model, setModelState] = useState('openrouter/google/gemini-2.0-flash-001')
  const [availableModels, setAvailableModels] = useState([])
  const [maxSteps, setMaxStepsState] = useState(10)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  function loadConfig() {
    setError(null)
    setLoading(true)
    apiGet('/config')
      .then(data => {
        setModelState(data.default_model)
        setAvailableModels(data.available_models)
        setMaxStepsState(data.default_max_steps)
        setError(null)
      })
      .catch(e => setError(e.message || 'Config load failed'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadConfig()
  }, [])

  function setModel(newModel) {
    setModelState(newModel)
    apiPut('/config', { default_model: newModel }).catch(() => {})
  }

  function setMaxSteps(n) {
    setMaxStepsState(n)
    apiPut('/config', { default_max_steps: n }).catch(() => {})
  }

  return { model, setModel, availableModels, maxSteps, setMaxSteps, loading, error, reload: loadConfig }
}
