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
import asyncio


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
    BrowserNavigateAction,
    BrowserClickAction,
    BrowserTypeAction,
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
        
        # Browser integration (lazy-loaded)
        self._browser_provider = None
        self._browser_controller = None
    
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
            
            # Browser actions - route to CDP controller
            elif isinstance(action, (BrowserNavigateAction, BrowserClickAction, BrowserTypeAction)):
                return self._handle_browser_action(action)
                
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
    
    def _handle_scroll(self, action: ScrollAction) -> None:
        """Handle SCROLL action."""
        scroll(action.amount)
    
    def _handle_press_key(self, action: PressKeyAction) -> None:
        """Handle PRESS_KEY action."""
        press_key(action.key)
    
    def _handle_type(self, action: TypeAction) -> None:
        """Handle TYPE action."""
        type_text(action.text)
    
    def _handle_wait(self, action: WaitAction) -> None:
        """Handle WAIT action."""
        wait(action.seconds)
    
    def _handle_browser_action(self, action: Action) -> ExecutionResult:
        """Handle browser-specific actions via CDP."""
        try:
            # Allow nested event loops for browser actions
            import nest_asyncio
            nest_asyncio.apply()
            result = asyncio.run(self._execute_browser_action(action))
            return ExecutionResult(
                ok=result.get("success", False),
                error=result.get("error")
            )
        except Exception as e:
            return ExecutionResult(ok=False, error=f"Browser action failed: {e}")
    
    async def _execute_browser_action(self, action: Action) -> dict:
        """Execute browser action async."""
        # Ensure browser connection
        if not await self._ensure_browser_connected():
            return {"success": False, "error": "Chrome not connected"}
        
        controller = self._browser_controller
        
        if isinstance(action, BrowserNavigateAction):
            return await controller.navigate(action.url)
        elif isinstance(action, BrowserClickAction):
            return await controller.click_element(action.element_index)
        elif isinstance(action, BrowserTypeAction):
            return await controller.type_into_element(action.element_index, action.text)
        
        return {"success": False, "error": "Unknown browser action"}
    
    async def _ensure_browser_connected(self) -> bool:
        """Ensure browser provider and controller are connected."""
        if self._browser_controller:
            return True
        
        try:
            from ..perception.browser_state import BrowserStateProvider
            from .browser_controller import BrowserController
            
            self._browser_provider = BrowserStateProvider()
            if await self._browser_provider.connect():
                self._browser_controller = BrowserController(self._browser_provider._page)
                return True
        except Exception:
            pass
        
        return False

    # ─────────────────────────────────────────────────────────────
    # ACCESSIBILITY STATE READING (Phase 1)
    # These methods read desktop state WITHOUT using vision
    # ─────────────────────────────────────────────────────────────

    def get_active_window(self) -> Optional[WindowInfo]:
        """
        Get information about the currently focused window.
        Uses xdotool to query the active window and xprop for the class.
        
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
            
            # Get window class (app name) using xprop WM_CLASS
            # xprop returns: WM_CLASS(STRING) = "thunar", "Thunar"
            # We want the second value (the class name)
            app_name = ""
            try:
                class_result = subprocess.run(
                    ["xprop", "-id", window_id, "WM_CLASS"],
                    capture_output=True, text=True, timeout=2
                )
                if class_result.returncode == 0 and "=" in class_result.stdout:
                    # Parse: WM_CLASS(STRING) = "instance", "ClassName"
                    parts = class_result.stdout.split("=", 1)[1].strip()
                    # Extract class names from quoted strings
                    import re
                    names = re.findall(r'"([^"]*)"', parts)
                    if len(names) >= 2:
                        app_name = names[1]  # ClassName (e.g., "Thunar")
                    elif len(names) == 1:
                        app_name = names[0]
            except Exception:
                pass
            
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
        Uses wmctrl to enumerate windows and xdotool for class names.
        
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
                    
                    # Get app class name via xprop WM_CLASS (convert hex wmctrl ID to decimal)
                    app_name = ""
                    try:
                        dec_id = str(int(wid, 16))
                        class_result = subprocess.run(
                            ["xprop", "-id", dec_id, "WM_CLASS"],
                            capture_output=True, text=True, timeout=1
                        )
                        if class_result.returncode == 0 and "=" in class_result.stdout:
                            import re
                            names = re.findall(r'"([^"]*)"', class_result.stdout)
                            if len(names) >= 2:
                                app_name = names[1]
                            elif len(names) == 1:
                                app_name = names[0]
                    except Exception:
                        pass
                    
                    windows.append(WindowInfo(
                        window_id=str(int(wid, 16)),  # Store as decimal for xdotool compat
                        title=title,
                        app_name=app_name,
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
        state = {
            "active_app": active.app_name if active else "",
            "window_title": active.title if active else "",
            "focused_element": "",  # TODO: implement AT-SPI query
        }
        
        # Add browser state if Chrome is active
        if self.is_browser_active():
            browser_state = self.get_browser_state()
            if browser_state:
                state["current_url"] = browser_state.url
                state["is_browser"] = True
                state["interactive_elements"] = browser_state.format_elements_for_llm()
                if browser_state.focused_element:
                    state["focused_element"] = str(browser_state.focused_element)
        
        return state
    
    def is_browser_active(self) -> bool:
        """Check if Chrome browser is currently active."""
        active = self.get_active_window()
        if not active:
            return False
        # Check both app_name and window_title for Chrome
        app = active.app_name.lower() if active.app_name else ""
        title = active.title.lower() if active.title else ""
        return "chrome" in app or "chromium" in app or "chrome" in title
    
    def get_browser_state(self):
        """Get current browser state via CDP (sync wrapper)."""
        try:
            import nest_asyncio
            nest_asyncio.apply()
            return asyncio.run(self._get_browser_state_async())
        except Exception as e:
            print(f"Failed to get browser state: {e}")
            return None
    
    async def _get_browser_state_async(self):
        """Get browser state async."""
        if not await self._ensure_browser_connected():
            return None
        return await self._browser_provider.get_state()


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
