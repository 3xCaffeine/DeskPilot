# AI Context Document (DO NOT DELETE)

## Project Overview
We are building a Computer Use Agent (CUA) that controls a desktop inside Docker using an LLM.
Loop: Screenshot → LLM decides action JSON → Executor performs click/type/scroll → repeat.

## Frozen Contracts (DO NOT CHANGE WITHOUT TEAM AGREEMENT)
1) Action Schema: src/.../schemas/actions.py
2) LLM Interface: src/.../llm/base.py
3) Executor Interface: src/.../execution/executor.py

## Current Status (Update Daily)
- Docker Desktop: ⏳
- Execution Layer (click/type): ⏳
- LLM Client (Gemini): ⏳
- Agent Core Loop: ⏳
- Integration / CLI: ⏳

## Key Decisions
- Runs saved to runs/{timestamp}/ with screenshots + metadata.json
- Action format is strict JSON (CLICK/TYPE/SCROLL/PRESS_KEY/WAIT/DONE/FAIL)
- Everyone works in separate folders to avoid merge conflicts

## File Ownership
- Person 1 (Integration/CLI/Tests): app/, scripts/, tests/
- Person 2 (Sandbox/Execution): docker/, execution/
- Person 3 (LLM/Agent Logic): llm/, agent/, schemas/

## Integration Points
### Agent → LLM
Agent calls:
- llm.get_next_action(screenshot, goal, history) -> Action

### Agent → Executor
Agent calls:
- executor.execute(action) -> {ok: true/false}

## MVP Demo Goal
Task 001: Open Chrome → type google.com → press Enter → DONE
