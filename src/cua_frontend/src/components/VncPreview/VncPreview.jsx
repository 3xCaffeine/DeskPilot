import './VncPreview.css'

const VNC_URL = 'http://localhost:6080/vnc.html?autoconnect=true&resize=scale&show_dot=true'

export default function VncPreview() {
  return (
    <div className="vnc-wrap">
      <div className="vnc-bar">
        <span className="vnc-dot" />
        <span className="vnc-label">Live Desktop</span>
        <a className="vnc-open" href={VNC_URL} target="_blank" rel="noreferrer" title="Open in new tab">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
            <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
          </svg>
        </a>
      </div>
      <iframe
        src={VNC_URL}
        className="vnc-frame"
        title="Live Desktop"
        allow="clipboard-read; clipboard-write"
      />
    </div>
  )
}
