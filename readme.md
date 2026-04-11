# DeskPilot — Computer Use Agent

DeskPilot is an accessibility-first agent that uses local OCR and multi-step planning to automate desktop tasks. It consists of a high-performance Python backend and a modern React frontend dashboard.

---

## 🏗️ Project Structure

The project is divided into two symmetric sub-projects:

*   **`src/cua_backend/`**: The Python world. Managed by `uv`. Contains the agent core, planner, and FastAPI server.
*   **`src/cua_frontend/`**: The React world. Managed by `Bun`. Contains the web-based dashboard and live execution viewer.

---

## 🐍 Backend Execution (Python)

The backend is managed by `uv`. All commands should be run from the `src/cua_backend` directory.

### Setup
```bash
cd src/cua_backend
uv sync
```

### Running the API Server (for Frontend)
This starts the FastAPI server which the frontend dashboard connects to.
```bash
cd src/cua_backend
python api_server.py
```
*Server runs at: `http://localhost:8000`*

### Running the CLI Agent
Execute tasks directly from your command line.
```bash
cd src/cua_backend
docker exec -it deskpilot-desktop python3 /app/src/cua_backend/run.py "Open Chrome and search for lo-fi music" --model "openrouter/google/gemini-2.0-flash-001"
```

---

## ⚛️ Frontend Execution (React)

The frontend is managed by `Bun`. All commands should be run from the `src/cua_frontend` directory.

### Setup
```bash
cd src/cua_frontend
bun install
```

### Development Server
```bash
cd src/cua_frontend
bun run dev
```
*UI runs at: `http://localhost:5173` (proxies `/api` to the backend)*

---

## 🐳 Docker Management

DeskPilot uses Docker to provide a sandbox environment for the agent to interact with.

### Build & Start
```bash
# From the project root
docker-compose -f docker/docker-compose.yml up --build -d
```

### Accessing the Virtual Desktop
*   **Browser**: [http://localhost:6080/vnc.html](http://localhost:6080/vnc.html)
*   **VNC Client**: `localhost:5900`

---

## 📂 Detailed Structure

```
DeskPilot/
│
├── src/
│   ├── cua_frontend/          # Web-based UI (React + Bun)
│   │   ├── src/               # React source
│   │   ├── package.json
│   │   └── vite.config.js     # Proxy setup for backend
│   │
│   └── cua_backend/           # Agent Logic & API (Python + uv)
│       ├── api/               # FastAPI routes & schemas
│       ├── agent/             # Core state machine & logic
│       ├── app/               # CLI entry points
│       ├── pyproject.toml     # uv configuration
│       ├── run.py             # CLI runner
│       └── api_server.py      # Web server runner
│
├── configs/                   # Shared configurations
├── docker/                    # Virtual environment (X11, VNC, NoVNC)
├── docs/                      # Extensive implementation plans
└── runs/                      # Agent execution logs & screenshots
```