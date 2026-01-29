"""
execution - Desktop control module
===================================
Provides the ability to control a desktop environment programmatically.

USAGE:
    from cua_backend.execution import DesktopController, ExecutionResult
    
    controller = DesktopController()
    screenshot = controller.screenshot()
    result = controller.execute(some_action)
"""

from .executor import Executor, ExecutionResult
from .desktop_controller import DesktopController, create_controller, WindowInfo

__all__ = [
    "Executor",
    "ExecutionResult", 
    "DesktopController",
    "create_controller",
    "WindowInfo",
]
