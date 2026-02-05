"""
Browser Controller - CDP-based browser automation via Playwright
Handles navigation, clicking, typing, form submission in Chrome browser.
"""
from typing import Optional, Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout


class BrowserController:
    """Execute browser actions via CDP connection."""
    
    def __init__(self, page: Page):
        """Initialize with connected Playwright page."""
        self._page = page
    
    async def navigate(self, url: str, timeout: int = 30000) -> Dict[str, Any]:
        """Navigate to URL."""
        try:
            response = await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            return {
                "success": True,
                "url": self._page.url,
                "status": response.status if response else None
            }
        except PlaywrightTimeout:
            return {"success": False, "error": f"Navigation timeout after {timeout}ms"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def click_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """Click element by CSS selector."""
        try:
            await self._page.click(selector, timeout=timeout)
            return {"success": True, "selector": selector}
        except PlaywrightTimeout:
            return {"success": False, "error": f"Element not found: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def type_into_element(self, selector: str, text: str, timeout: int = 5000) -> Dict[str, Any]:
        """Type text into input element."""
        try:
            await self._page.fill(selector, text, timeout=timeout)
            return {"success": True, "selector": selector, "text_length": len(text)}
        except PlaywrightTimeout:
            return {"success": False, "error": f"Input not found: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def submit_form(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """Submit form by selector (form or submit button)."""
        try:
            # Try to click submit button or press Enter on form
            element = await self._page.query_selector(selector)
            if not element:
                return {"success": False, "error": f"Form not found: {selector}"}
            
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == "form":
                await element.evaluate("form => form.submit()")
            else:
                await element.click(timeout=timeout)
            
            return {"success": True, "selector": selector}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def wait_for_navigation(self, timeout: int = 30000) -> Dict[str, Any]:
        """Wait for page navigation to complete."""
        try:
            await self._page.wait_for_load_state("domcontentloaded", timeout=timeout)
            return {"success": True, "url": self._page.url}
        except PlaywrightTimeout:
            return {"success": False, "error": f"Navigation timeout after {timeout}ms"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def wait_for_selector(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        """Wait for element to appear."""
        try:
            await self._page.wait_for_selector(selector, timeout=timeout, state="visible")
            return {"success": True, "selector": selector}
        except PlaywrightTimeout:
            return {"success": False, "error": f"Element did not appear: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def scroll_page(self, direction: str = "down", amount: int = 500) -> Dict[str, Any]:
        """Scroll page up or down."""
        try:
            scroll_y = amount if direction == "down" else -amount
            await self._page.evaluate(f"window.scrollBy(0, {scroll_y})")
            return {"success": True, "direction": direction, "amount": amount}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def press_key(self, key: str) -> Dict[str, Any]:
        """Press keyboard key (Enter, Tab, Escape, etc)."""
        try:
            await self._page.keyboard.press(key)
            return {"success": True, "key": key}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_element_text(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """Get text content from element."""
        try:
            text = await self._page.text_content(selector, timeout=timeout)
            return {"success": True, "text": text or ""}
        except PlaywrightTimeout:
            return {"success": False, "error": f"Element not found: {selector}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
