"""
actions.py - Low-level action functions
========================================
These are the "primitive" operations our agent can do.
Each function uses PyAutoGUI to control the desktop.

WHY SEPARATE FROM desktop_controller.py?
- Single Responsibility: This file = raw PyAutoGUI calls
- desktop_controller.py = orchestration + error handling

HOW PYAUTOGUI WORKS:
PyAutoGUI talks to whatever display is in the DISPLAY env var.
Inside Docker, DISPLAY=:99 points to our Xvfb virtual screen.
"""

from __future__ import annotations

import time
import pyautogui
from PIL import Image


# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

# PyAutoGUI has a safety feature: move mouse to corner = abort
# Disable it since we're in a container
pyautogui.FAILSAFE = False

# Add tiny delays between actions for stability
pyautogui.PAUSE = 0.1


# ─────────────────────────────────────────────────────────────
# ACTION FUNCTIONS
# ─────────────────────────────────────────────────────────────

def click(x: int, y: int) -> None:
    """
    Click at coordinates (x, y).
    
    HOW IT WORKS:
    1. Move mouse to (x, y)
    2. Press and release left mouse button
    
    Args:
        x: Horizontal position (0 = left edge)
        y: Vertical position (0 = top edge)
    """
    pyautogui.click(x, y)


def double_click(x: int, y: int) -> None:
    """Double-click at coordinates (x, y)."""
    pyautogui.doubleClick(x, y)


def right_click(x: int, y: int) -> None:
    """Right-click at coordinates (x, y)."""
    pyautogui.rightClick(x, y)


def type_text(text: str, interval: float = 0.02) -> None:
    """
    Type text character by character.
    
    WHY interval=0.02?
    Too fast and some apps miss keystrokes.
    0.02 seconds per char = 50 chars/second = fast but reliable.
    
    Args:
        text: String to type
        interval: Delay between each character
    """
    pyautogui.typewrite(text, interval=interval)


def press_key(key: str) -> None:
    """
    Press a special key or key combination.
    
    EXAMPLES:
        press_key("enter")        # Press Enter
        press_key("tab")          # Press Tab
        press_key("ctrl+a")       # Select all (Ctrl+A)
        press_key("ctrl+shift+t") # Reopen closed tab
    
    HOW COMBINATIONS WORK:
    We split on "+" and use hotkey() for multiple keys.
    """
    if "+" in key:
        # It's a combo like "ctrl+c"
        keys = [k.strip().lower() for k in key.split("+")]
        pyautogui.hotkey(*keys)
    else:
        # Single key
        pyautogui.press(key.lower())


def scroll(amount: int) -> None:
    """
    Scroll the mouse wheel.
    
    Args:
        amount: Positive = scroll UP (content moves down)
                Negative = scroll DOWN (content moves up)
                
    NOTE: The "amount" is in "clicks" of the scroll wheel.
          3 is usually one page-ish.
    """
    pyautogui.scroll(amount)


def move_mouse(x: int, y: int) -> None:
    """Move mouse to (x, y) without clicking."""
    pyautogui.moveTo(x, y)


def drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> None:
    """
    Click and drag from one point to another.
    Useful for: selecting text, moving windows, sliders.
    """
    pyautogui.moveTo(start_x, start_y)
    pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)


def screenshot() -> Image.Image:
    """
    Capture the current screen.
    
    Returns:
        PIL Image object of the screenshot
        
    HOW IT WORKS:
    PyAutoGUI uses 'scrot' on Linux to capture the screen.
    scrot reads from the DISPLAY env variable.
    """
    return pyautogui.screenshot()


def wait(seconds: float) -> None:
    """
    Wait for a specified duration.
    
    WHY NEEDED?
    - Wait for page to load
    - Wait for animation to finish
    - Wait for app to start
    """
    time.sleep(seconds)
