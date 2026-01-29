"""
ocr.py - Local OCR processing
============================
Provides fast, local text extraction using Tesseract.
Used for "Are We There Yet?" local goal verification.
"""

from __future__ import annotations
from typing import List
from PIL import Image
import pytesseract

def get_text_from_image(image: Image.Image) -> str:
    """Extract all text from a PIL image using Tesseract."""
    try:
        # We use a simple config for better speed
        return pytesseract.image_to_string(image).strip()
    except Exception as e:
        print(f"OCR Error: {e}")
        return ""

def check_text_exists(image: Image.Image, keywords: List[str]) -> bool:
    """
    Check if any of the keywords exist on the screen.
    Case-insensitive.
    """
    text = get_text_from_image(image).lower()
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False

def contains_goal_indicators(image: Image.Image, goal: str) -> bool:
    """
    Smart check: Does the screen contain words from the goal?
    (e.g., if goal is 'search google', check for 'Google')
    """
    # Simply extract significant words from goal
    words = [w.strip(",.?!") for w in goal.split() if len(w) > 3]
    return check_text_exists(image, words)
