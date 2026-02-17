"""
planner.py - DSPy-based Text-Only Planner
==========================================
Decides the next action using ONLY text state (no screenshots).
This is the DECIDE phase of the state machine.

DSPy handles:
- Deciding action type (keyboard vs wait vs done)
- Determining if vision escalation is needed
- Mapping intent to frozen Action schema
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Literal, List
import dspy


# ─────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────

@dataclass
class TextState:
    """Non-visual state collected during OBSERVE phase."""
    active_app: str = ""
    window_title: str = ""
    focused_element: str = ""  # role + label if available
    current_url: Optional[str] = None  # Browser URL if active
    is_browser: bool = False  # True if Chrome is active window
    interactive_elements: str = ""  # Indexed list of clickable elements
    

@dataclass
class PlannerInput:
    """Everything the planner needs to decide next action."""
    goal: str
    step: int
    history: List[str] = None # List of [Action: Result] strings
    text_state: TextState = None
    
    def __post_init__(self):
        if self.history is None:
            self.history = []
        if self.text_state is None:
            self.text_state = TextState()


@dataclass  
class PlannerOutput:
    """Structured decision from the planner."""
    action_type: Literal[
        "PRESS_KEY", "TYPE", "WAIT", "DONE", "FAIL", "CLICK", "SCROLL",
        "BROWSER_NAVIGATE", "BROWSER_CLICK", "BROWSER_TYPE"
    ]
    action_param: str = ""  # key name, text to type, or seconds
    expected_window_title: str = "" # Anchor for local verification
    success_indicators: str = "" # Comma-separated success markers
    sub_goals: str = "" # Comma-separated list of steps to achieve the final goal
    reason: str = ""
    needs_vision: bool = False
    confidence: float = 0.8


# ─────────────────────────────────────────────────────────────
# DSPy SIGNATURE (defines input/output contract)
# ─────────────────────────────────────────────────────────────

class PlanNextAction(dspy.Signature):
    """
    Decide the next sequence of actions to achieve the goal using accessibility-first principles.
    
    STANDARD SKILLS:
    - Open App: PRESS_KEY("ESCAPE"); WAIT(0.5); PRESS_KEY("Alt+F2"); WAIT(1.5); TYPE("app-name"); PRESS_KEY("ENTER")
    - File Path Navigation: PRESS_KEY("Ctrl+L"); WAIT(1); TYPE("/app/path"); PRESS_KEY("ENTER"); WAIT(1) (MANDATORY for finding files)
    - File/Save Dialogs: PRESS_KEY("Ctrl+S"); WAIT(1); TYPE("filename"); PRESS_KEY("ENTER") (CRITICAL: Always WAIT after Ctrl+S/Ctrl+O)
    
    **CRITICAL TASK PARSING**:
    When goal has multiple parts like "go to X and search for Y":
    - Step 1: Navigate to X (success_indicators: EMPTY)
    - Step 2: Search for Y on X (success_indicators: "Y, search results")
    - "search [site]" = BROWSER_NAVIGATE([site].com), NOT searching for site name in Google
    
    BROWSER CDP ACTIONS (when is_browser=True and interactive_elements provided):
    - BROWSER_NAVIGATE(url) - Navigate directly to URL
    - BROWSER_CLICK(index) - Click element at index (e.g., BROWSER_CLICK(3) clicks [3])
    - BROWSER_TYPE(index, text) - Type into element at index (does NOT auto-submit)
    
    DO NOT use CSS selectors. ONLY use index numbers from interactive_elements list.
    
    GUIDELINES:
    1. Output a SEMICOLON-SEPARATED sequence of actions to save LLM calls.
    2. **SEQUENCE LENGTH POLICY**: Keep sequences short (MAX 5-8 actions). Do NOT try to complete complex tasks in one sequence. It is better to finish a sub-goal, verify, and then plan the next step.
    3. **AUTOCOMPLETE/DROPDOWN POLICY**: Elements marked [SEARCH_INPUT] or [DROPDOWN_OPTION] indicate an autocomplete flow.
       - STEP A: When you see [SEARCH_INPUT], type into it: output ONLY BROWSER_TYPE(index, text). STOP. No more actions.
       - STEP B: After typing, the next observation will show [DROPDOWN_OPTION] items. BROWSER_CLICK the one whose text best matches your search.
       - NEVER type AND click in the same sequence for autocomplete inputs. Element indices CHANGE after typing.
       - Example flow: Step 1: BROWSER_TYPE(5, "Tokyo") → Step 2: BROWSER_CLICK(8) where [8] is the [DROPDOWN_OPTION] for "Tokyo, Japan".
    4. **POPUP/MODAL HANDLING**: If you see elements with text like "Close", "Dismiss", "Accept", "×", or buttons that appear to be popup closers (usually at high indices, overlaying content), dismiss them FIRST before continuing. Try PRESS_KEY(ESCAPE) as safest option, or BROWSER_CLICK on close button index. Do NOT try to interact with content behind popups - close them first.
    5. **BROWSER PRIORITY**: When is_browser=True and interactive_elements are provided, ALWAYS use index-based BROWSER_* actions (BROWSER_NAVIGATE, BROWSER_CLICK(index), BROWSER_TYPE(index, text)). Never use TYPE or PRESS_KEY for web interactions - they are unreliable in browsers. Only use indices from the interactive_elements list.
    6. If the goal is reached, use the DONE action.
    7. **ANTI-LOOP POLICY**: If history shows REPEATED FAILURES (same action failing 2+ times), you are STUCK. Use recovery:
       - Browser stuck? Use BROWSER_NAVIGATE to go back to the target site
       - Wrong page? Check current_url and navigate directly: BROWSER_NAVIGATE(correctsite.com)
       - Can't find element? Scroll to reveal more elements (SCROLL) or escalate: needs_vision=True
       DO NOT repeat the same failing action more than twice.
    8. GOAL DECOMPOSITION: Break down the main goal into 3-5 sub_goals. Each sub_goal must be a specific, verifiable state (e.g. 'Firefox Opened', 'Search results loaded', 'article page active').
    9. **CRITICAL COMPLETION POLICY**: ONLY set 'success_indicators' when the FINAL step that completes the ENTIRE goal is being executed.
       - Opening apps, navigating to sites → success_indicators: "" (ALWAYS EMPTY for intermediate steps)
       - Only the LAST action that fulfills the goal → success_indicators: "expected content keywords"
       - Multi-part goals: Each sub-goal except the final one has EMPTY success_indicators
    10. WEB BEHAVIOR: Search results are INTERMEDIATE. If the user asks for 'info' or 'scrape', you MUST navigate into a specific website. Do NOT use DONE on a Google/Bing/Search result page. Use Vision fallback if you need to click a specific link.
    11. **SOFT ANCHORS**: Use GENERIC 'expected_window_title' like 'Google Chrome' NOT specific sites like 'Amazon.com' - page titles are dynamic and will cause false mismatches.
    12. **DIALOG TIMING**: Transition windows like "Save As" or "Open File" appear slowly. Always include a WAIT(1) after the trigger key (Ctrl+S, Ctrl+O) and before typing the filename.
    13. **ABSOLUTE PATHS**: In Thunar, ALWAYS use File Path Navigation (Ctrl+L) to go to specific folders (e.g., '/app/docs'). Do NOT rely on clicking folders in the view as they might be hidden. The base path is ALWAYS /app, not /home/user.
    14. **LAUNCHER RECOVERY**: If the window title is "app" or "application finder" after you sent ENTER, the launcher is stuck on top. Use PRESS_KEY("ESCAPE") and WAIT(1) to clear it. Do NOT try to use Alt+F2 again in the same sequence. Stop after ESCAPE so you can see if the target app was actually launched behind it.
    """
    
    # Inputs
    goal: str = dspy.InputField(desc="The task goal to achieve")
    app_knowledge: str = dspy.InputField(desc="Knowledge base of app names and titles")
    history: str = dspy.InputField(desc="String representation of previous actions and their outcomes")
    step: int = dspy.InputField(desc="Current step number (1-indexed)")
    window_title: str = dspy.InputField(desc="Current window title (via xdotool)")
    active_app: str = dspy.InputField(desc="Currently focused application")
    current_url: str = dspy.InputField(desc="Current browser URL (if in Chrome, otherwise empty)")
    is_browser: bool = dspy.InputField(desc="True if currently in Chrome browser")
    focused_element: str = dspy.InputField(desc="Currently focused input element (if any)")
    interactive_elements: str = dspy.InputField(desc="Indexed list of clickable elements: [1] <A> 'Link', [2] <BUTTON> 'Submit' (browser only)")
    
    # Outputs
    action_sequence: str = dspy.OutputField(desc="Semicolon-separated actions. Use BROWSER_NAVIGATE to go to websites when is_browser=True.")
    expected_window_title: str = dspy.OutputField(desc="**SOFT ANCHOR**: Generic title like 'Google Chrome', never specific page names.")
    success_indicators: str = dspy.OutputField(desc="**CRITICAL**: Comma-separated strings visible ONLY when ENTIRE goal complete. EMPTY for intermediate steps.")
    sub_goals: str = dspy.OutputField(desc="Comma-separated sub-tasks (e.g., 'Navigate to site, Search for query, View results')")
    reason: str = dspy.OutputField(desc="Reasoning for this sequence")
    needs_vision: bool = dspy.OutputField(desc="Set to True ONLY if text signals are insufficient")


# ─────────────────────────────────────────────────────────────
# DSPy MODULE (the actual planner logic)
# ─────────────────────────────────────────────────────────────

class ActionPlanner(dspy.Module):
    """
    Multi-step text-only planner.
    """
    
    def __init__(self):
        super().__init__()
        self.planner = dspy.ChainOfThought(PlanNextAction)
        self.knowledge = self._load_knowledge()

    def _load_knowledge(self) -> str:
        try:
            import yaml
            import os
            from pathlib import Path
            path = Path("configs/xfce_apps.yaml")
            if path.exists():
                with open(path, "r") as f:
                    return str(yaml.safe_load(f))
            return "No app knowledge available."
        except:
            return "No app knowledge available."
    
    def forward(self, inp: PlannerInput) -> PlannerOutput:
        """Run the planner and return a sequence-aware output."""
        # Convert history list to string for dspy
        history_str = "\n".join(inp.history) if inp.history else "none"
        
        result = self.planner(
            goal=inp.goal,
            app_knowledge=self.knowledge,
            history=history_str,
            step=inp.step,
            window_title=inp.text_state.window_title or "unknown",
            active_app=inp.text_state.active_app or "unknown",
            current_url=inp.text_state.current_url or "",
            is_browser=inp.text_state.is_browser,
            focused_element=inp.text_state.focused_element or "",
            interactive_elements=inp.text_state.interactive_elements or "",
        )
        
        return PlannerOutput(
            action_type="SEQUENCE",
            action_param=result.action_sequence,
            expected_window_title=result.expected_window_title,
            success_indicators=getattr(result, 'success_indicators', ""),
            sub_goals=getattr(result, 'sub_goals', ""),
            reason=result.reason,
            needs_vision=getattr(result, 'needs_vision', False),
        )


# ─────────────────────────────────────────────────────────────
# PLANNER WRAPPER (easy-to-use interface)
# ─────────────────────────────────────────────────────────────

class Planner:
    """
    High-level planner interface for the agent.
    
    Usage:
        planner = Planner()
        planner.configure("gemini/gemini-2.0-flash")
        
        output = planner.decide(PlannerInput(
            goal="Open Firefox and search for cats",
            step=1,
            text_state=TextState(window_title="Desktop", active_app="xfce4-panel")
        ))
    """
    
    def __init__(self):
        self._module = ActionPlanner()
        self._configured = False
    
    def configure(self, model: str = "gemini/gemini-2.5-flash"):
        """Configure DSPy with the specified model."""
        import os
        
        # If openrouter, we need to ensure LiteLLM has the key
        if model.startswith("openrouter/"):
            os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY", "")
            
        lm = dspy.LM(model)
        dspy.configure(lm=lm)
        self._configured = True
    
    def decide(self, inp: PlannerInput) -> PlannerOutput:
        """
        Decide the next action based on text state.
        
        Args:
            inp: PlannerInput with goal, step, and text state
            
        Returns:
            PlannerOutput with action decision
        """
        if not self._configured:
            raise RuntimeError("Planner not configured. Call configure() first.")
        
        return self._module(inp)


# ─────────────────────────────────────────────────────────────
# ACTION MAPPING (convert planner output to frozen Action)
# ─────────────────────────────────────────────────────────────

import re

def parse_actions(output: PlannerOutput) -> list:
    """
    Parses a sequence string like 'PRESS_KEY(Alt+F2); TYPE(firefox)'
    into a list of Action objects.
    """
    from ..schemas.actions import (
        PressKeyAction, TypeAction, WaitAction, DoneAction, FailAction, ScrollAction,
        BrowserNavigateAction, BrowserClickAction, BrowserTypeAction, Action
    )
    
    actions = []
    # Split by semicolon, but handle potential whitespace
    parts = [p.strip() for p in output.action_param.split(";") if p.strip()]
    
    for part in parts:
        # Check for standalone tokens like DONE or FAIL
        if part.upper() == "DONE":
            actions.append(DoneAction(final_answer="Goal reached", reason=output.reason))
            continue
        if part.upper() == "FAIL":
            actions.append(FailAction(error="Task failed", reason=output.reason))
            continue

        # Regex to match TYPE(param) or TYPE("param") or BROWSER_TYPE(selector, text)
        match = re.match(r"(\w+)\((.*)\)", part)
        if not match:
            continue
            
        a_type = match.group(1).upper()
        a_param = match.group(2).strip("'\"") # Remove quotes
        
        # Handle browser actions with multiple parameters
        if a_type.startswith("BROWSER_"):
            # Clean up common LLM mistakes like url='amazon.com' or selector='input'
            # Extract just the values, stripping parameter names if present
            cleaned_params = []
            for p in a_param.split(",", 1):
                p = p.strip().strip("'\"")
                # Remove parameter names like "url=", "selector=", "text="
                if '=' in p:
                    p = p.split('=', 1)[1].strip("'\"")
                cleaned_params.append(p)
            
            if a_type == "BROWSER_NAVIGATE":
                url = cleaned_params[0] if cleaned_params else ""
                actions.append(BrowserNavigateAction(url=url, reason=output.reason))
            elif a_type == "BROWSER_CLICK":
                try:
                    index = int(cleaned_params[0]) if cleaned_params else 0
                    actions.append(BrowserClickAction(element_index=index, reason=output.reason))
                except ValueError:
                    pass  # Skip invalid index
            elif a_type == "BROWSER_TYPE":
                try:
                    index = int(cleaned_params[0]) if len(cleaned_params) > 0 else 0
                    text = cleaned_params[1] if len(cleaned_params) > 1 else ""
                    actions.append(BrowserTypeAction(element_index=index, text=text, reason=output.reason))
                except ValueError:
                    pass  # Skip invalid index
            continue
        
        # Regular desktop actions
        if a_type == "PRESS_KEY":
            actions.append(PressKeyAction(key=a_param, reason=output.reason))
        elif a_type == "TYPE":
            actions.append(TypeAction(text=a_param, reason=output.reason))
        elif a_type == "WAIT":
            try:
                sec = float(a_param) if a_param else 1.0
            except:
                sec = 1.0
            actions.append(WaitAction(seconds=sec, reason=output.reason))
        elif a_type == "DONE":
            actions.append(DoneAction(final_answer=a_param or "Goal reached", reason=output.reason))
        elif a_type == "SCROLL":
            try:
                # amount can be 'down' or a number. If 'down' we use a default
                val = -10 if a_param.lower() == "down" else 10 if a_param.lower() == "up" else int(a_param)
            except:
                val = -10
            actions.append(ScrollAction(amount=val, reason=output.reason))
        elif a_type == "FAIL":
            actions.append(FailAction(error=a_param or "Task failed", reason=output.reason))
            
    return actions or [FailAction(error=f"Failed to parse sequence: {output.action_param}", reason=output.reason)]
