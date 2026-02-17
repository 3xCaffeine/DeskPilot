# Computer Use Agent - Complete Repository Structure

## Quick Docker Commands

### Build & Start
```bash
# Build the Docker image
docker-compose -f docker/docker-compose.yml build

# Start container in background
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

### Access Container
```bash
# Enter container shell
docker exec -it deskpilot-desktop bash

# Start Chrome with CDP
DISPLAY=:99 /usr/local/bin/chrome-with-cdp &

```

### Example Command
```bash
# Run a specific task
docker exec -it deskpilot-desktop python3 /app/run.py "Create a folder called documents and copy the file from docs into that newly created folder" --model "openrouter/google/gemini-2.0-flash-001"
```

### Vision-only Smoke Test (bypasses DSPy planner)

Use this to verify that vision calling (Gemini/OpenRouter) works end-to-end:

```bash
# Vision-only loop: screenshot -> vision LLM -> one Action -> execute
docker exec -it deskpilot-desktop python3 /app/scripts/vision_only.py "Open Chrome" --model "openrouter/google/gemini-2.0-flash-001" --max-steps 10
```

Notes:
- Provider is inferred from `--model` (`openrouter/...` vs `gemini/...`).
- Outputs are saved under `runs/<run_id>/vision_only/`.

### Container Management
```bash
# Stop container
docker-compose -f docker/docker-compose.yml down

# Restart container
docker-compose -f docker/docker-compose.yml restart

# Remove container and volumes
docker-compose -f docker/docker-compose.yml down -v

# View running containers
docker ps

# Check container resource usage
docker stats deskpilot-desktop
```

### VNC Access
```bash
# Access desktop via browser
# URL: http://localhost:6080/vnc.html

# Or use VNC client on port 5900
# Connection: localhost:5900
```

### Debugging
```bash
# Check if Chrome is running
docker exec -it deskpilot-desktop bash -c "ps aux | grep chrome"

# Test CDP connection
docker exec -it deskpilot-desktop bash -c "curl http://127.0.0.1:9222/json"

# View Chrome wrapper script
docker exec -it deskpilot-desktop bash -c "cat /usr/local/bin/chrome-with-cdp"

# Check environment variables
docker exec -it deskpilot-desktop bash -c "env | grep DISPLAY"
```

---

## Repository Structure

```
computer-use-agent/
│
├── .github/
│   └── workflows/
│       └── ci.yml                    # GitHub Actions (optional, for later)
│
├── docker/
│   ├── Dockerfile                    # Main desktop environment
│   ├── docker-compose.yml            # Easy container orchestration
│   ├── entrypoint.sh                 # Container startup script
│   └── supervisord.conf              # Process manager config (VNC + desktop)
│
├── configs/
│   ├── agent_config.yaml             # Agent settings (max steps, timeouts)
│   └── model_config.yaml             # Gemini model parameters
│
├── tasks/
│   ├── task_001_open_chrome.yaml
│   ├── task_002_search_query.yaml
│   └── task_003_extract_info.yaml
│
├── runs/                             # Generated at runtime
│   └── {timestamp}/
│       ├── screenshots/
│       ├── actions.json
│       └── metadata.json
│
├── tests/
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_executor.py
│   └── test_schemas.py
│
├── src/
│   └── cua_backend/                          # "cua" = Computer Use Agent
│       ├── __init__.py
│       │
│       ├── app/
│       │   ├── __init__.py
│       │   └── main.py               # Entry point: python -m cua.app.main
│       │
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── core.py               # Main agent loop (observe → think → act)
│       │   └── state.py              # Agent state management
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── base.py               # Base LLM interface
│       │   ├── gemini_client.py      # Gemini API wrapper
│       │   └── prompt_templates.py   # System prompts for the agent
│       │
│       ├── perception/
│       │   ├── __init__.py
│       │   ├── screenshot.py         # Capture screenshots
│       │   └── ocr.py                # Optional: text extraction (later)
│       │
│       ├── execution/
│       │   ├── __init__.py
│       │   ├── executor.py           # Base executor interface
│       │   ├── actions.py            # click, type, scroll, press_key
│       │   └── desktop_controller.py # Interact with Docker desktop
│       │
│       ├── schemas/
│       │   ├── __init__.py
│       │   ├── actions.py            # Action schema (Pydantic models)
│       │   └── tasks.py              # Task definition schema
│       │
│       ├── evaluation/
│       │   ├── __init__.py
│       │   ├── metrics.py            # Success rate, completion time
│       │   └── validator.py          # Check if task completed correctly
│       │
│       └── utils/
│           ├── __init__.py
│           ├── logger.py             # Structured logging
│           └── config_loader.py      # Load YAML configs
│
├── scripts/
│   ├── setup_docker.sh               # One-command Docker setup
│   ├── run_task.sh                   # Quick task runner
│   └── view_run.py                   # Display run results
│
├── .env.example                      # Template for environment variables
├── .gitignore
├── pyproject.toml                    
├── README.md
└── LICENSE
```