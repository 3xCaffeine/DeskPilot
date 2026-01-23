"""
Logging utilities for the Computer Use Agent.
Provides structured logging with configurable levels.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__).
        level: Log level (DEBUG, INFO, WARNING, ERROR). 
               Defaults to CUA_LOG_LEVEL env var or INFO.
               
    Returns:
        Configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # Only configure if not already configured
        log_level = level or os.environ.get("CUA_LOG_LEVEL", "INFO")
        logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logger.level)
        
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger
