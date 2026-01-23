"""
Screenshot capture functionality for the Computer Use Agent.
Provides local screenshot capture for testing purposes.
"""

from __future__ import annotations

from PIL import Image

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None


def capture_screenshot() -> Image.Image:
    """
    Capture a screenshot of the current desktop.
    
    This is for LOCAL TESTING only. In production, the executor
    provides screenshots from the Docker container.
    
    Returns:
        PIL Image of the current screen.
        
    Raises:
        RuntimeError: If screenshot capture is not available.
    """
    if ImageGrab is None:
        raise RuntimeError(
            "PIL.ImageGrab is not available on this platform. "
            "Use the executor.screenshot() method instead."
        )

    try:
        screenshot = ImageGrab.grab()
        return screenshot
    except Exception as e:
        raise RuntimeError(f"Failed to capture screenshot: {e}") from e


def save_screenshot(image: Image.Image, path: str) -> None:
    """Save a screenshot to the specified path."""
    image.save(path)
