import { useState, useEffect } from 'react';
import { apiGet, apiPut } from '../api/client';
import './Settings.css';

const EyeIcon = () => (
  <svg viewBox="0 0 24 24"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
);
const EyeOffIcon = () => (
  <svg viewBox="0 0 24 24"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></svg>
);

export default function Settings() {
  const [config, setConfig] = useState(null);
  const [model, setModel] = useState('');
  const [customModel, setCustomModel] = useState('');
  const [maxSteps, setMaxSteps] = useState(10);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    apiGet('/config').then(c => {
      setConfig(c);
      setModel(c.default_model);
      setMaxSteps(c.default_max_steps);
    }).catch(() => setError('Failed to load config'));
  }, []);

  const handleSave = async () => {
    try {
      const m = customModel.trim() || model;
      const body = { default_model: m, default_max_steps: maxSteps };
      if (openrouterKey.trim()) body.openrouter_api_key = openrouterKey.trim();
      if (geminiKey.trim()) body.gemini_api_key = geminiKey.trim();
      await apiPut('/config', body);
      setSaved(true);
      setOpenrouterKey('');
      setGeminiKey('');
      setTimeout(() => setSaved(false), 2000);
    } catch {
      setError('Failed to save');
    }
  };

  const [openrouterKey, setOpenrouterKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [showOrKey, setShowOrKey] = useState(false);
  const [showGemKey, setShowGemKey] = useState(false);

  return (
    <div className="settings-page">
      <h2 className="settings-title">Settings</h2>

      {error && <div className="settings-error">{error}</div>}

      {/* Model Configuration */}
      <section className="settings-card">
        <h3 className="settings-section-title">Model Configuration</h3>
        <label className="settings-label">Default Model</label>
        <select
          className="settings-select"
          value={model}
          onChange={e => setModel(e.target.value)}
        >
          {config?.available_models.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <label className="settings-label" style={{ marginTop: 12 }}>Custom Model (override)</label>
        <input
          className="input"
          placeholder="e.g. openrouter/meta-llama/llama-3-70b"
          value={customModel}
          onChange={e => setCustomModel(e.target.value)}
        />
      </section>

      {/* Execution Defaults */}
      <section className="settings-card">
        <h3 className="settings-section-title">Execution Defaults</h3>
        <label className="settings-label">Max Steps: <strong>{maxSteps}</strong></label>
        <input
          type="range" min={1} max={50} value={maxSteps}
          onChange={e => setMaxSteps(Number(e.target.value))}
          className="settings-slider"
        />
      </section>

      {/* System Status */}
      <section className="settings-card">
        <h3 className="settings-section-title">System Status</h3>
        <div className="settings-status-row">
          <span className="settings-label">Docker Container</span>
          <span className={`settings-dot ${config?.docker_status === 'running' ? 'dot-green' : 'dot-red'}`} />
          <span className="settings-status-text">{config?.docker_status ?? '…'}</span>
        </div>
        <div className="settings-status-row">
          <span className="settings-label">noVNC</span>
          <a href={config?.vnc_url} target="_blank" rel="noreferrer" className="settings-link">
            {config?.vnc_url}
          </a>
        </div>
      </section>

      {/* API Keys */}
      <section className="settings-card">
        <h3 className="settings-section-title">API Keys</h3>
        <p className="settings-key-hint">Leave blank to keep existing value. Saved to <code>configs/settings.json</code> on the backend.</p>
        <label className="settings-label">OPENROUTER_API_KEY {config?.openrouter_key_set && <span className="dot-set">● set</span>}</label>
        <div className="settings-key-field">
          <input
            type={showOrKey ? 'text' : 'password'}
            className="input"
            placeholder={config?.openrouter_key_set ? '••••••••  (already set)' : 'sk-or-...'}
            value={openrouterKey}
            onChange={e => setOpenrouterKey(e.target.value)}
            autoComplete="new-password"
          />
          <button className="key-toggle" onClick={() => setShowOrKey(v => !v)} title={showOrKey ? 'Hide' : 'Show'}>
            {showOrKey ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        </div>
        <label className="settings-label" style={{ marginTop: 10 }}>GEMINI_API_KEY {config?.gemini_key_set && <span className="dot-set">● set</span>}</label>
        <div className="settings-key-field">
          <input
            type={showGemKey ? 'text' : 'password'}
            className="input"
            placeholder={config?.gemini_key_set ? '••••••••  (already set)' : 'AIza...'}
            value={geminiKey}
            onChange={e => setGeminiKey(e.target.value)}
            autoComplete="new-password"
          />
          <button className="key-toggle" onClick={() => setShowGemKey(v => !v)} title={showGemKey ? 'Hide' : 'Show'}>
            {showGemKey ? <EyeOffIcon /> : <EyeIcon />}
          </button>
        </div>
      </section>

      <div className="settings-save-bar">
        {saved && <span className="settings-save-feedback">✓ Changes saved</span>}
        <button className="settings-save-btn" onClick={handleSave}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          Save Changes
        </button>
      </div>
    </div>
  );
}
