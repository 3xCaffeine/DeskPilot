# DeskPilot — State Machine Diagram

> The agent runs an **O.D.E.V** loop: **Observe → Decide → Execute → Verify**, with an **Escalate** recovery path when verification fails.

---

## Main Agent Loop

```mermaid
flowchart TD
    Start(["User Goal"]) --> ss

    subgraph OBS["① OBSERVE — Build World Model"]
        ss["Take Screenshot"]
        dt["Read Window Title + App Class"]
        bc{"Chrome is the<br/>active window?"}
        cdp["CDP: get URL, Interactive<br/>Elements, Visible Text"]
        ts["Build combined Text State"]

        ss --> dt --> bc
        bc -->|Yes| cdp --> ts
        bc -->|No| ts
    end

    ts --> cc{"Quick check:<br/>goal already done?"}
    cc -->|"Yes"| Done
    cc -->|"No"| plan

    subgraph DEC["② DECIDE — Plan Next Actions"]
        plan["DSPy Planner reads<br/>state + history + goal"]
        out["Output: action_sequence,<br/>expected_anchor, success_indicators"]
        par["Parse into Action objects"]

        plan --> out --> par
    end

    par --> dispatch

    subgraph EXE["③ EXECUTE — Run Actions"]
        dispatch{"Action Type?"}
        desk["Desktop via PyAutoGUI<br/>CLICK, TYPE, SCROLL,<br/>PRESS_KEY, WAIT"]
        brw["Browser via CDP<br/>NAVIGATE, CLICK, TYPE<br/>using element index"]

        dispatch -->|"Desktop action"| desk
        dispatch -->|"Browser action"| brw
    end

    desk --> poll
    brw --> poll

    subgraph VER["④ VERIFY — Did It Work?"]
        poll["Poll ~5 sec for anchor match<br/>(App class, Title, URL, Keywords)"]
        found{"Anchor<br/>matched?"}
        si{"Success indicators<br/>found on screen?"}
        ok["Step Verified"]
        nok["Not Verified"]

        poll --> found
        found -->|"Yes"| si
        si -->|"Yes or N/A"| ok
        si -->|"No"| nok
        found -->|"No"| nok
    end

    ok --> more{"More steps<br/>needed?"}
    more -->|"Yes: next step"| ss
    more -->|"No: goal complete"| Done

    nok --> retry{"Retry left?<br/>(max 2 per step)"}
    retry -->|"Yes"| dispatch
    retry -->|"Exhausted"| cdpv

    subgraph ESC["⑤ ESCALATE — Recovery"]
        cdpv{"Chrome<br/>active?"}
        cdpchk["CDP Verify:<br/>check URL + page text"]
        vis["Vision Fallback:<br/>screenshot sent to<br/>Gemini or OpenRouter"]
        fix["Execute single<br/>corrective action"]
        ok2["Verified via CDP"]

        cdpv -->|"Yes"| cdpchk
        cdpchk -->|"Verified"| ok2
        cdpchk -->|"Still failing"| vis
        cdpv -->|"No"| vis
        vis --> fix
    end

    ok2 --> more
    fix --> ss

    Done(["DONE: return TaskResult"])
```

---

## Phase Details

| Phase | What Happens | Key Code |
|-------|-------------|----------|
| **① OBSERVE** | Screenshot saved to `runs/<run_id>/step_XXX.png`. Desktop state via `xdotool` / `xprop`. If Chrome is active, CDP gives URL, indexed interactive elements, and visible text. | `agent/core.py`, `perception/browser_state.py`, `execution/desktop_controller.py` |
| **② DECIDE** | DSPy `ChainOfThought` planner outputs a semicolon-separated action sequence, a soft anchor (expected window title / URL), and success indicators. App knowledge loaded from `configs/xfce_apps.yaml`. | `agent/planner.py` |
| **③ EXECUTE** | Desktop actions run through PyAutoGUI on `DISPLAY=:99`. Browser actions use Playwright CDP — the same `FIND_ELEMENTS_JS` ensures element indices match between OBSERVE and EXECUTE. | `execution/actions.py`, `execution/browser_controller.py` |
| **④ VERIFY** | Polls for ~5 sec checking: app class match → window title match → URL match → keyword intersection. If anchor found + success indicators present → verified. Otherwise → retry or escalate. | `agent/core.py` |
| **⑤ ESCALATE** | **Layer 1 — CDP:** re-check URL and page text without a screenshot. **Layer 2 — Vision:** send screenshot to Gemini or OpenRouter, get back one corrective action, execute it, then loop back to OBSERVE. Forced if `consecutive_failures >= 3`. | `llm/gemini_client.py`, `llm/openrouter_client.py` |

---

## Key Design Rules

- **Index-based browser targeting** — interactive elements are numbered `[0], [1], …` by a shared JS snippet (`FIND_ELEMENTS_JS`). The planner references these indices; the executor clicks/types by the same indices.
- **Autocomplete safety** — type in one step, pick the dropdown option in the *next* step (indices go stale after DOM changes).
- **Popup-first** — always dismiss popups/modals before interacting with content underneath.
- **Vision is expensive** — it is only called after local + CDP verification both fail, never in the normal happy path.
