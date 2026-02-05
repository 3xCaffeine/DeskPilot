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
    action_type: Literal["PRESS_KEY", "TYPE", "WAIT", "DONE", "FAIL", "CLICK", "SCROLL"]
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
    - Open App: PRESS_KEY("Alt+F2"); WAIT(1); TYPE("app_name"); PRESS_KEY("ENTER")
    - Info Search: PRESS_KEY("Ctrl+L"); WAIT(0.5); TYPE("Topic info summary"); PRESS_KEY("ENTER") (Always add 'info summary' for deep-dives)
    - Browser Navigation: If info is not visible, use SCROLL("down") or PRESS_KEY("pagedown").
    
    GUIDELINES:
    1. Output a SEMICOLON-SEPARATED sequence of actions to save LLM calls.
    2. Example sequence: PRESS_KEY(Alt+F2); WAIT(1); TYPE(firefox); PRESS_KEY(ENTER)
    3. If the goal is reached, use the DONE action.
    4. REPETITION POLICY: If history shows you've tried an action before and it failed or didn't show success markers, DO NOT REPEAT IT. Instead, use an investigation action like 'ls' or 'SCROLL' or 'WAIT'.
    5. GOAL DECOMPOSITION: Break down the main goal into 3-5 sub_goals. Each sub_goal must be a specific, verifiable state (e.g. 'Firefox Opened', 'Search results loaded', 'article page active').
    6. COMPLETION POLICY: ONLY provide 'success_indicators' if this action sequence completes the ENTIRE goal. If this is an intermediate step (e.g. just opening the browser), leave 'success_indicators' EMPTY.
    7. WEB BEHAVIOR: Search results are INTERMEDIATE. If the user asks for 'info' or 'scrape', you MUST navigate into a specific website. Do NOT use DONE on a Google/Bing/Search result page. Use Vision fallback if you need to click a specific link.
    8. SOFT ANCHORS: For browsers, use GENERIC 'expected_window_title' (e.g. 'Mozilla Firefox' or 'Google Search') rather than the exact page title, as titles are dynamic.
    """
    
    # Inputs
    goal: str = dspy.InputField(desc="The task goal to achieve")
    app_knowledge: str = dspy.InputField(desc="Knowledge base of app names and titles")
    history: str = dspy.InputField(desc="String representation of previous actions and their outcomes")
    step: int = dspy.InputField(desc="Current step number (1-indexed)")
    window_title: str = dspy.InputField(desc="Current window title (via xdotool)")
    active_app: str = dspy.InputField(desc="Currently focused application")
    
    # Outputs
    action_sequence: str = dspy.OutputField(desc="Sequence of actions (e.g., PRESS_KEY(Alt+F2); WAIT(1); TYPE(firefox); PRESS_KEY(ENTER))")
    expected_window_title: str = dspy.OutputField(desc="The window title expected after this sequence (e.g., 'Mozilla Firefox' or 'Terminal')")
    success_indicators: str = dspy.OutputField(desc="Comma-separated strings that prove the ENTIRE goal is reached. Leave EMPTY for intermediate steps.")
    sub_goals: str = dspy.OutputField(desc="Comma-separated list of all sub-tasks needed to finish (e.g., 'Open Browser, Search Google, Click Result')")
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
        PressKeyAction, TypeAction, WaitAction, DoneAction, FailAction, ScrollAction, Action
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

        # Regex to match TYPE(param) or TYPE("param")
        match = re.match(r"(\w+)\((.*)\)", part)
        if not match:
            continue
            
        a_type = match.group(1).upper()
        a_param = match.group(2).strip("'\"") # Remove quotes
        
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
