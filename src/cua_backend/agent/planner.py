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
from typing import Optional, Literal
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
    

@dataclass
class PlannerInput:
    """Everything the planner needs to decide next action."""
    goal: str
    step: int
    last_action: str = ""
    last_action_ok: bool = True
    verification_passed: bool = True
    text_state: TextState = None
    
    def __post_init__(self):
        if self.text_state is None:
            self.text_state = TextState()


@dataclass  
class PlannerOutput:
    """Structured decision from the planner."""
    action_type: Literal["PRESS_KEY", "TYPE", "WAIT", "DONE", "FAIL", "CLICK"]
    action_param: str = ""  # key name, text to type, or seconds
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
    - Web Search: PRESS_KEY("Ctrl+L"); WAIT(0.5); TYPE("url/query"); PRESS_KEY("ENTER")
    
    GUIDELINES:
    1. Output a SEMICOLON-SEPARATED sequence of actions to save LLM calls.
    2. Example sequence: PRESS_KEY(Alt+F2); WAIT(1); TYPE(firefox); PRESS_KEY(ENTER)
    3. If the goal is reached, use the DONE action.
    """
    
    # Inputs
    goal: str = dspy.InputField(desc="The task goal to achieve")
    step: int = dspy.InputField(desc="Current step number (1-indexed)")
    last_action: str = dspy.InputField(desc="Previous action taken")
    window_title: str = dspy.InputField(desc="Current window title (via xdotool)")
    active_app: str = dspy.InputField(desc="Currently focused application")
    
    # Outputs
    action_sequence: str = dspy.OutputField(desc="One or more actions separated by ; (e.g., PRESS_KEY(Alt+F2); WAIT(1); TYPE(firefox); PRESS_KEY(ENTER))")
    reason: str = dspy.OutputField(desc="Reasoning for this specific sequence")
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
    
    def forward(self, inp: PlannerInput) -> PlannerOutput:
        """Run the planner and return a sequence-aware output."""
        result = self.planner(
            goal=inp.goal,
            step=inp.step,
            last_action=inp.last_action or "none",
            window_title=inp.text_state.window_title or "unknown",
            active_app=inp.text_state.active_app or "unknown",
        )
        
        return PlannerOutput(
            action_type="SEQUENCE", # Marker for multi-action
            action_param=result.action_sequence,
            reason=result.reason,
            needs_vision=result.needs_vision if hasattr(result, 'needs_vision') else False,
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

def parse_actions(output: PlannerOutput) -> List[Action]:
    """
    Parses a sequence string like 'PRESS_KEY(Alt+F2); TYPE(firefox)'
    into a list of Action objects.
    """
    from ..schemas.actions import (
        PressKeyAction, TypeAction, WaitAction, DoneAction, FailAction
    )
    
    actions = []
    # Split by semicolon, but handle potential whitespace
    parts = [p.strip() for p in output.action_param.split(";") if p.strip()]
    
    for part in parts:
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
            actions.append(DoneAction(final_answer=a_param or None, reason=output.reason))
        elif a_type == "FAIL":
            actions.append(FailAction(error=a_param or "Task failed", reason=output.reason))
            
    return actions or [FailAction(error=f"Failed to parse sequence: {output.action_param}", reason=output.reason)]
