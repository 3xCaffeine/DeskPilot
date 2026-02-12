"""Perception module for the Computer Use Agent."""

from .screenshot import capture_screenshot, save_screenshot

# Browser state (optional - graceful import)
try:
    from .browser_state import BrowserState, BrowserStateProvider
    __all__ = [
        "capture_screenshot",
        "save_screenshot",
        "BrowserState",
        "BrowserStateProvider",
    ]
except ImportError:
    # Playwright not available - browser state disabled
    __all__ = [
        "capture_screenshot",
        "save_screenshot",
    ]
