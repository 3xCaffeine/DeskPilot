# DeskPilot Architecture & Flow (0 → 100)

This is the most detailed, code-backed guide to how DeskPilot works end-to-end:

1. How the Linux desktop is created in Docker (XFCE + Xvfb + VNC/noVNC)
2. How Chrome is launched with CDP enabled and how Playwright connects to it
3. How the agent runs an **O.D.E.V** loop (Observe → Decide → Execute → Verify → Escalate)
4. How “index-based browser actions” work (Jetski-like element indices)
5. How verification and the escalation ladder reduce fragile vision calls

If you want to understand “what is being used for everything” (CDP, PyAutoGUI, DSPy, OCR, OpenRouter/Gemini), this document is that wiring diagram.

---

## 1) System Overview

DeskPilot is a “computer use agent” that can operate a full desktop environment.

Two execution surfaces exist:

- **Desktop surface**: mouse/keyboard actions via PyAutoGUI (X11 display inside Docker).
- **Browser surface (Chrome)**: programmatic, index-based interactions via CDP + Playwright, bypassing brittle pixel clicks.

Key idea: use the cheapest, highest-confidence signals first (window titles, app classes, current URL, DOM element lists), and use screenshots/vision only when those signals fail.

---

## 2) Runtime Environment (Docker Desktop-in-a-Container)

DeskPilot is designed to run inside a Linux container even if your host OS is Windows.

### Container processes

The container runs multiple long-lived processes using Supervisord:

- **Xvfb**: virtual display `:99` (the “monitor”) at `1280x720x24`
- **D-Bus session**: required for Chrome
- **XFCE**: lightweight desktop session on `DISPLAY=:99`
- **x11vnc**: VNC server so you can view/control the desktop
- **noVNC/websockify**: browser-based VNC client

These are configured in `docker/supervisord.conf`.

### Ports and access

- VNC: `localhost:5900`
- noVNC: `http://localhost:6080/vnc.html`

These mappings are in `docker/docker-compose.yml`.

### Chrome + CDP (DevTools Protocol)

Chrome is installed in the image and wrapped so it always launches with CDP enabled.

The wrapper script is created in `docker/Dockerfile` as `/usr/local/bin/chrome-with-cdp` with key flags:

- `--remote-debugging-port=9222` (CDP endpoint)
- `--user-data-dir=/tmp/chrome-profile` (clean disposable profile)
- various flags to suppress first-run, sign-in, background services

In the container you typically start it like:

```bash
DISPLAY=:99 /usr/local/bin/chrome-with-cdp &
```

CDP health check:

```bash
curl http://127.0.0.1:9222/json
```

---

## 3) Entry Points & High-Level Call Graph

### CLI entry

- `run.py` adds `src/` to `sys.path` and calls the CLI main.
- `src/cua_backend/app/main.py` parses args and wires up the system.

Main wiring responsibilities:

1. Configure the **text-only planner** (DSPy model name is passed via `--model`)
2. Pick the **vision fallback** provider (Gemini vs OpenRouter) based on the model string
3. Create a `DesktopController` executor
4. Create an `Agent(planner, executor, vision_llm)` and run a `Task`

### Core runtime objects

- `Agent` (`src/cua_backend/agent/core.py`): orchestrates the O.D.E.V loop
- `Planner` (`src/cua_backend/agent/planner.py`): uses DSPy to output **a semicolon-separated action sequence** + anchors
- `DesktopController` (`src/cua_backend/execution/desktop_controller.py`): executes actions (desktop via PyAutoGUI, browser via CDP)
- `BrowserStateProvider` (`src/cua_backend/perception/browser_state.py`): reads browser state over CDP
- `BrowserController` (`src/cua_backend/execution/browser_controller.py`): executes browser actions over CDP using **element indices**

---

## 4) Data Contracts (Schemas)

DeskPilot uses a strict action schema so the “Decide” step produces machine-executable objects.

Defined in `src/cua_backend/schemas/actions.py`:

### Desktop actions

- `CLICK(x, y)`
- `TYPE(text)`
- `SCROLL(amount)`
- `PRESS_KEY(key)`
- `WAIT(seconds)`
- `DONE(final_answer?)`
- `FAIL(error)`

### Browser (CDP) actions

- `BROWSER_NAVIGATE(url)`
- `BROWSER_CLICK(element_index)`
- `BROWSER_TYPE(element_index, text)`

Important: browser actions are **index-based**, not selector-based. The index refers to the interactive elements list collected during observation.

Tasks live in `src/cua_backend/schemas/tasks.py`:

- `Task(goal, max_steps, run_id)`
- `TaskResult(success, steps_taken, final_answer?, error?, run_id?)`

---

## 5) The O.D.E.V Loop (Observe → Decide → Execute → Verify → Escalate)

The agent loop is implemented in `src/cua_backend/agent/core.py` in `Agent.run()`.

### Step lifecycle

For each step (1..max_steps):

1. **Observe**
2. **(Optional) local completion check**
3. **Decide** a short action sequence
4. **Execute** the sequence (with small local retry)
5. **Verify** via anchors (polling)
6. **Escalate** to CDP verification and then vision if still stuck

Screenshots are saved every step to `runs/<run_id>/step_XXX.png`, and each action is recorded as a `StepRecord` in memory.

---

## 6) OBSERVE: Building a “TextState” World Model

DeskPilot tries hard to observe using non-visual signals first.

### Desktop text state

Collected by `DesktopController.get_text_state()`:

- Active window title via `xdotool getwindowname`
- Active app class via `xprop WM_CLASS` (more stable than titles)
- Focused element (placeholder for AT-SPI; currently best-effort)

### Browser-enriched text state (when Chrome is active)

If Chrome is the active window (`DesktopController.is_browser_active()`), DeskPilot enriches the observed state with CDP data:

- `current_url`
- `interactive_elements` (indexed list)
- `focused_element` (DOM active element)

This is provided by `BrowserStateProvider.get_state()` over CDP.

---

## 7) Browser State via CDP (Playwright over Chrome DevTools)

### How CDP is used

DeskPilot does not drive Playwright’s bundled browser. Instead it:

1. Launches **system Chrome** with `--remote-debugging-port=9222`
2. Uses Playwright’s CDP connector:

```python
await playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
```

This is implemented in `BrowserStateProvider.connect()`.

### What state is extracted

`BrowserStateProvider.get_state()` returns a `BrowserState`:

- `url`, `title`
- `is_loading` (from `document.readyState`)
- `focused_element` (from `document.activeElement`)
- `visible_text` (from `document.body.innerText`, truncated)
- `interactive_elements` (the crucial indexed list)

---

## 8) Index-Based Interactive Elements (Jetski-like targeting)

This is the core reliability feature for web automation.

### The shared enumeration contract

Both perception (OBSERVE) and execution (BROWSER_CLICK/TYPE) must build the *same* ordered list of elements.

That guarantee is enforced by a single shared JS snippet:

- `src/cua_backend/utils/constants.py` defines:
    - `INTERACTIVE_SELECTOR`
    - `FIND_ELEMENTS_JS`

`FIND_ELEMENTS_JS`:

- selects common interactive tags/roles (`a`, `button`, `input`, `[role=option]`, etc.)
- filters to visible, viewport elements via bounding box checks
- filters out “empty spacer” elements (keeps inputs even if they have no visible text)
- produces a stable `allEls[]` list

### Indexing rules

- Indices are **0-based** (because the browser state extraction uses `map((el, i) => index: i)`)
- The LLM must refer to the index as printed in the observation list

### LLM-facing formatting + markers

`BrowserState.format_elements_for_llm()` produces lines like:

```text
[0] <INPUT> "Search" [SEARCH_INPUT]
[8] <BUTTON> "Tokyo, Japan" [DROPDOWN_OPTION]
[21] <BUTTON> "×" [POPUP_CLOSER?]
```

Markers are heuristic but important:

- `[SEARCH_INPUT]`: likely combobox/search fields
- `[DROPDOWN_OPTION]`: likely autocomplete suggestion items (`role=option/menuitem`)
- `[POPUP_CLOSER?]`: likely modal/popup close/accept buttons

---

## 9) DECIDE: Text-Only Planning with DSPy

DeskPilot’s default planning is text-only:

- It uses DSPy (`dspy.LM`, `dspy.configure`) to run a `ChainOfThought` module.
- Planner logic lives in `src/cua_backend/agent/planner.py`.

### Inputs to the planner

The planner sees:

- goal
- step number
- history (last actions/outcomes)
- text state: title/app/url/focused element + interactive elements list if in browser
- app knowledge from `configs/xfce_apps.yaml` (loaded by the planner)

### Output contract: short sequences + anchors

The planner returns:

- `action_sequence`: semicolon-separated actions (max ~5–8 recommended)
- `expected_window_title`: a **soft anchor** used in verification (keep generic)
- `success_indicators`: comma-separated “done markers” (should be non-empty only for the final goal-completing step)
- `sub_goals`: checklist string to keep the agent oriented

### Turning text into Actions

`parse_actions()` converts the sequence string into Pydantic action objects.

Browser actions support multiple parameters:

- `BROWSER_NAVIGATE(url)`
- `BROWSER_CLICK(index)`
- `BROWSER_TYPE(index, text)`

The parser also strips common LLM mistakes like `url=` or `text=` prefixes.

---

## 10) EXECUTE: Desktop vs Browser Dispatch

Execution happens through `DesktopController.execute()`.

### Desktop execution

Desktop actions are implemented in `src/cua_backend/execution/actions.py` via PyAutoGUI:

- Clicks, typing, scrolling, key combos
- Runs against `DISPLAY=:99` (Xvfb)
- Uses tiny pauses for stability

### Browser execution

Browser actions are routed to CDP:

1. `DesktopController` lazily connects to Chrome via `BrowserStateProvider.connect()`
2. `BrowserController` receives a Playwright `Page`
3. `BrowserController` executes:
     - Navigate: `page.goto(url)`
     - Click: `page.evaluate(FIND_ELEMENTS_JS + allEls[idx].click())`
     - Type: focus/click then `page.keyboard.type(text)`

Key reliability choices:

- `BrowserController` uses the same `FIND_ELEMENTS_JS` as perception → indices match
- It treats “execution context destroyed” errors during click/type as success because that typically means navigation happened
- `BROWSER_TYPE` intentionally does **not** auto-submit (to avoid auto-submit loops)

---

## 11) VERIFY: Anchors, Polling, and Fuzzy Matching

After executing a sequence, the agent verifies that the world changed as predicted.

Implemented in `Agent.run()`:

### Anchor verification strategy (in order)

For up to ~5 seconds of polling:

1. **Active app class match** (most stable for desktop apps)
2. **Window title substring match**
3. **Browser URL substring match** (when in Chrome)
4. **Keyword intersection** (fuzzy, multi-word fallback)

If the anchor is not found, the agent attempts a recovery:

- enumerate all windows via `wmctrl -l`
- if expected app/title exists in the background, focus it with `xdotool windowactivate`

### Completion criteria (strict)

DeskPilot avoids premature “DONE” by requiring:

- anchor match (title/app/url) AND
- **success indicators** present on screen (via OCR), when indicators are provided

This policy is used both at the top of the step (fast completion check) and after sequences.

---

## 12) ESCALATE: CDP Verification → Vision Fallback

If verification fails locally, DeskPilot escalates in layers.

### When does vision actually get called? (Exact thresholds)

Vision calling is *not* part of the normal loop. It happens only after local verification fails.

Current behavior in `Agent.run()` (`src/cua_backend/agent/core.py`):

- **Local retry budget per step:** the agent attempts the planned sequence up to **2 times** (`for attempt in range(2)`).
- **Within each attempt:** it polls for the expected anchor for up to **~5 seconds** (`for poll_attempt in range(5)`).
- If, after those retries, the step is still not `verified`, ESCALATE begins.
- **CDP-first:** if Chrome is active, the agent tries CDP verification (URL / page text markers) before spending a vision call.
- **Vision call condition:** it calls vision only if it is still not `verified` *and* a vision client is configured.
- **Forced vision on loops:** if `consecutive_failures >= 3` and vision is configured, it forces a vision escalation even if CDP “looks OK” (common case: popups/modals).

### Layer 1: CDP verification (when in browser)

Before spending a vision call, the agent re-checks using browser state:

- URL contains expected anchor string
- `BrowserState.visible_text` contains any success markers

This is faster and more reliable than OCR for web content.

### Layer 2: Vision fallback (screenshot → one corrective action)

If still not verified (or a loop is detected), the agent calls `vision_llm.get_next_action()`.

Vision providers implement `LLMClient` (`src/cua_backend/llm/base.py`) and must return a single valid `Action`.

- Gemini: `src/cua_backend/llm/gemini_client.py`
    - Uses `google.genai`
    - Enforces strict JSON-only responses, with retries on parse/validation errors

- OpenRouter: `src/cua_backend/llm/openrouter_client.py`
    - Uses `litellm.completion(...)`
    - Sends an image as base64 `data:image/png;base64,...`
    - Requests `response_format={"type": "json_object"}`

The vision prompt template is in `src/cua_backend/llm/prompt_templates.py` and strictly limits outputs to one JSON action.

---

## 13) Autocomplete, Popups, and Dynamic DOM (Why the Planner Has Special Rules)

Web apps frequently change the DOM after typing, which changes the interactive elements list.

DeskPilot addresses this with two combined mechanisms:

1. Shared element enumeration (`FIND_ELEMENTS_JS`) reduces noise and keeps indices consistent between observation and execution.
2. Planner policies (in the DSPy signature) enforce stable interaction patterns:

- **Autocomplete policy**:
    - Step A: `BROWSER_TYPE(search_input_index, "query")` and STOP
    - Step B: next loop, click a `[DROPDOWN_OPTION]`
    - Never type and click in the same sequence for autocomplete flows

- **Popup policy**:
    - dismiss popups first (ESCAPE or clicking `[POPUP_CLOSER?]`) before interacting with underlying content

These rules exist because indices often become stale after intermediate DOM updates.

---

## 14) Full Dataflow Diagram

```mermaid
flowchart TD
    U[User goal via CLI] --> CLI[run.py -> cua_backend/app/main.py]
    CLI --> A[Agent.run]

    subgraph Observe[OBSERVE]
        A --> SS[DesktopController.screenshot]
        A --> TS[DesktopController.get_text_state]
        TS -->|xdotool/xprop/wmctrl| X11[X11 window state]
        TS -->|if Chrome active| CDPState[BrowserStateProvider.get_state]
        CDPState -->|url + interactive_elements| TS
    end

    subgraph Decide[DECIDE]
        A --> P[Planner.decide (DSPy)]
        P --> Seq[PlannerOutput.action_sequence]
        Seq --> Parse[parse_actions -> Action objects]
    end

    subgraph Execute[EXECUTE]
        A --> DC[DesktopController.execute]
        DC -->|desktop actions| PyA[PyAutoGUI -> Xvfb :99]
        DC -->|browser actions| BC[BrowserController via CDP]
    end

    subgraph Verify[VERIFY]
        A --> Anch{Anchor match?}
        Anch -->|poll title/app/url| OK[Step success]
        Anch -->|no| Esc[ESCALATE]
    end

    subgraph Escalate[ESCALATE]
        Esc -->|browser? check url/text| CDPVerif[CDP verification]
        CDPVerif -->|still no| Vision[Vision LLM (Gemini/OpenRouter)]
        Vision --> One[One corrective Action]
        One --> DC
    end
```

---

## 15) How to Run (Practical)

### Build + start container

```bash
docker-compose -f docker/docker-compose.yml build
docker-compose -f docker/docker-compose.yml up -d
```

### Enter container + start Chrome CDP

```bash
docker exec -it deskpilot-desktop bash
DISPLAY=:99 /usr/local/bin/chrome-with-cdp &
```

### Run a task

```bash
docker exec -it deskpilot-desktop python3 /app/run.py "Your task here" --max-steps 10 --model "openrouter/google/gemini-2.0-flash-001"
```

---

## 16) Where to Look in Code (Map)

- Agent loop: `src/cua_backend/agent/core.py`
- Planner + parsing: `src/cua_backend/agent/planner.py`
- Desktop executor: `src/cua_backend/execution/desktop_controller.py`
- Desktop primitives: `src/cua_backend/execution/actions.py`
- Browser state (CDP): `src/cua_backend/perception/browser_state.py`
- Browser execution (CDP): `src/cua_backend/execution/browser_controller.py`
- Shared DOM enumeration: `src/cua_backend/utils/constants.py`
- Action schemas: `src/cua_backend/schemas/actions.py`
- Vision clients: `src/cua_backend/llm/gemini_client.py`, `src/cua_backend/llm/openrouter_client.py`
- Docker environment: `docker/Dockerfile`, `docker/supervisord.conf`, `docker/docker-compose.yml`
