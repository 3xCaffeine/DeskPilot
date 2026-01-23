# DeskPilot Setup Plan

Goal: Initialize the project with dependencies, a Task schema, and a CLI entry point.

## User Review Required
> [!NOTE]
> [src/cua_backend/schemas/tasks.py](file:///c:/Users/vaibh/Projects/cuavink/DeskPilot/src/cua_backend/schemas/tasks.py) and [src/cua_backend/agent/core.py](file:///c:/Users/vaibh/Projects/cuavink/DeskPilot/src/cua_backend/agent/core.py) are currently empty. I will initialize them with basic structures.

## Proposed Changes

### Configuration
#### [MODIFY] [pyproject.toml](file:///c:/Users/vaibh/Projects/cuavink/DeskPilot/pyproject.toml)
- Add dependencies: `google-generativeai`, `pydantic`, `pyyaml`, `pillow`, `pyautogui`.

### Source Code
#### [MODIFY] [src/cua_backend/schemas/tasks.py](file:///c:/Users/vaibh/Projects/cuavink/DeskPilot/src/cua_backend/schemas/tasks.py)
- Define `Task` Pydantic model.
- Attributes: `name` (str), `description` (str), `max_steps` (int, default=10).

#### [MODIFY] [src/cua_backend/agent/core.py](file:///c:/Users/vaibh/Projects/cuavink/DeskPilot/src/cua_backend/agent/core.py)
- Create `Agent` class.
- Add `run_task(self, task: Task)` method (skeleton implementation printing status).

#### [NEW] [src/cua_backend/main.py](file:///c:/Users/vaibh/Projects/cuavink/DeskPilot/src/cua_backend/main.py)
- Implement CLI using `argparse`.
- Argument: `task_file` (path to YAML).
- Logic: Load YAML, validate with `Task` schema, instantiate `Agent`, call `run_task`.

## Verification Plan

### Automated Tests
1. **Dependency Check**: Run `pip install .` or `uv sync` to verify dependencies resolve.
2. **CLI Test**:
   - Create a sample `test_task.yaml`.
   - Run `python -m src.cua_backend.main test_task.yaml`.
   - Verify output indicates agent is running the task.
