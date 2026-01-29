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

import subprocess
import time
from dataclasses import dataclass
from typing import Optional, List
from PIL import Image


# ─────────────────────────────────────────────────────────────
# DATA STRUCTURES FOR STATE READING
# ─────────────────────────────────────────────────────────────

@dataclass
class WindowInfo:
    """Information about a window from xdotool/wmctrl."""
    window_id: str
    title: str
    app_name: str = ""
    is_active: bool = False

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
    # ACCESSIBILITY STATE READING (Phase 1)
    # These methods read desktop state WITHOUT using vision
    # ─────────────────────────────────────────────────────────────

    def get_active_window(self) -> Optional[WindowInfo]:
        """
        Get information about the currently focused window.
        Uses xdotool to query the active window.
        
        Returns:
            WindowInfo with window_id, title, app_name, or None if failed
        """
        try:
            # Get active window ID
            result = subprocess.run(
                ["xdotool", "getactivewindow"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode != 0:
                return None
            
            window_id = result.stdout.strip()
            
            # Get window title
            title_result = subprocess.run(
                ["xdotool", "getwindowname", window_id],
                capture_output=True, text=True, timeout=2
            )
            title = title_result.stdout.strip() if title_result.returncode == 0 else ""
            
            # Get window class (app name)
            class_result = subprocess.run(
                ["xdotool", "getwindowclassname", window_id],
                capture_output=True, text=True, timeout=2
            )
            app_name = class_result.stdout.strip() if class_result.returncode == 0 else ""
            
            return WindowInfo(
                window_id=window_id,
                title=title,
                app_name=app_name,
                is_active=True
            )
        except Exception:
            return None

    def get_window_list(self) -> List[WindowInfo]:
        """
        Get list of all open windows.
        Uses wmctrl to enumerate windows.
        
        Returns:
            List of WindowInfo objects for each open window
        """
        windows = []
        try:
            # wmctrl -l: list windows with format "ID DESKTOP HOST TITLE"
            result = subprocess.run(
                ["wmctrl", "-l"],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode != 0:
                return windows
            
            # Get active window for comparison
            active = self.get_active_window()
            active_id = active.window_id if active else ""
            
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split(None, 3)  # Split into max 4 parts
                if len(parts) >= 4:
                    wid = parts[0]
                    title = parts[3]
                    windows.append(WindowInfo(
                        window_id=wid,
                        title=title,
                        is_active=(wid == active_id)
                    ))
                    
        except Exception:
            pass
        
        return windows

    def get_text_state(self):
        """
        Collect all text-based state for the OBSERVE phase.
        Returns a dict compatible with PlannerInput.text_state.
        """
        active = self.get_active_window()
        return {
            "active_app": active.app_name if active else "",
            "window_title": active.title if active else "",
            "focused_element": "",  # TODO: implement AT-SPI query
        }


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
