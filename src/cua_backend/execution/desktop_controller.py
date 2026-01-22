"""
desktop_controller.py - The Executor Implementation
====================================================
This is the class that the Agent uses to control the desktop.
It implements the Executor interface defined in executor.py.

DESIGN PATTERN:
- Executor (abstract) → defines WHAT actions are possible
- DesktopController   → defines HOW actions are performed

The Agent doesn't care HOW we click - just that we CAN click.
Tomorrow we could swap this for a Windows controller or a web controller.
"""

from __future__ import annotations

import time
from typing import Optional
from PIL import Image

from .executor import Executor, ExecutionResult
from .actions import (
    click,
    double_click,
    type_text,
    press_key,
    scroll,
    screenshot as take_screenshot,
    wait,
)
from ..schemas.actions import (
    Action,
    ClickAction,
    TypeAction,
    ScrollAction,
    PressKeyAction,
    WaitAction,
    DoneAction,
    FailAction,
)


class DesktopController(Executor):
    """
    Controls a Linux desktop via PyAutoGUI.
    
    USAGE:
        controller = DesktopController()
        
        # Take a screenshot
        img = controller.screenshot()
        
        # Execute an action
        result = controller.execute(ClickAction(x=100, y=200))
        
    HOW IT CONNECTS TO DOCKER:
    This code runs INSIDE the Docker container.
    PyAutoGUI talks to DISPLAY=:99 (our Xvfb virtual screen).
    The VNC server shows us what's happening.
    """
    
    def __init__(self, startup_delay: float = 0.0):
        """
        Initialize the desktop controller.
        
        Args:
            startup_delay: Seconds to wait before first action.
                          Useful to let the desktop fully load.
        """
        if startup_delay > 0:
            time.sleep(startup_delay)
    
    def screenshot(self) -> Image.Image:
        """
        Capture the current desktop.
        
        Returns:
            PIL Image of the screen (1280x720 by default)
        """
        return take_screenshot()
    
    def execute(self, action: Action) -> ExecutionResult:
        """
        Perform one action on the desktop.
        
        This is a "dispatcher" - it looks at action.type and calls
        the appropriate handler method.
        
        Args:
            action: One of ClickAction, TypeAction, ScrollAction, etc.
            
        Returns:
            ExecutionResult with ok=True if successful
        """
        try:
            # Dispatch based on action type
            # ────────────────────────────
            # Pattern: Check type → call handler → return success
            
            if isinstance(action, ClickAction):
                self._handle_click(action)
                
            elif isinstance(action, TypeAction):
                self._handle_type(action)
                
            elif isinstance(action, ScrollAction):
                self._handle_scroll(action)
                
            elif isinstance(action, PressKeyAction):
                self._handle_press_key(action)
                
            elif isinstance(action, WaitAction):
                self._handle_wait(action)
                
            elif isinstance(action, DoneAction):
                # Nothing to "do" - agent is signaling completion
                pass
                
            elif isinstance(action, FailAction):
                # Agent is signaling failure
                return ExecutionResult(ok=False, error=action.error)
                
            else:
                return ExecutionResult(
                    ok=False, 
                    error=f"Unknown action type: {type(action).__name__}"
                )
            
            return ExecutionResult(ok=True)
            
        except Exception as e:
            # Catch any PyAutoGUI errors
            return ExecutionResult(ok=False, error=str(e))
    
    # ─────────────────────────────────────────────────────────────
    # PRIVATE HANDLER METHODS
    # Each one translates an Action object into raw PyAutoGUI calls
    # ─────────────────────────────────────────────────────────────
    
    def _handle_click(self, action: ClickAction) -> None:
        """Handle CLICK action."""
        click(action.x, action.y)
    
    def _handle_type(self, action: TypeAction) -> None:
        """Handle TYPE action."""
        type_text(action.text)
    
    def _handle_scroll(self, action: ScrollAction) -> None:
        """Handle SCROLL action."""
        scroll(action.amount)
    
    def _handle_press_key(self, action: PressKeyAction) -> None:
        """Handle PRESS_KEY action."""
        press_key(action.key)
    
    def _handle_wait(self, action: WaitAction) -> None:
        """Handle WAIT action."""
        wait(action.seconds)


# ─────────────────────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────────────────────

def create_controller(wait_for_desktop: bool = True) -> DesktopController:
    """
    Factory function to create a DesktopController.
    
    Args:
        wait_for_desktop: If True, wait 2 seconds for desktop to be ready
        
    Returns:
        A ready-to-use DesktopController
    """
    delay = 2.0 if wait_for_desktop else 0.0
    return DesktopController(startup_delay=delay)
