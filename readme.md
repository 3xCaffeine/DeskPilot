# Computer Use Agent - Complete Repository Structure

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