"""
Browser Controller - CDP-based browser automation via Playwright
Handles navigation, clicking, typing in Chrome browser using index-based element targeting.
"""
from typing import Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ..utils.constants import INTERACTIVE_SELECTOR


class BrowserController:
    """Execute browser actions via CDP connection."""
    
    def __init__(self, page: Page):
        """Initialize with connected Playwright page."""
        self._page = page
    
    async def navigate(self, url: str, timeout: int = 30000) -> Dict[str, Any]:
        """Navigate to URL. Auto-adds https:// if no protocol specified."""
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://', 'file://', 'about:', 'chrome://')):
                url = f'https://{url}'
            
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
    
    async def click_element(self, index: int, timeout: int = 5000) -> Dict[str, Any]:
        """Click element by its index from the interactive elements list."""
        try:
            clicked = await self._page.evaluate(f"""
                (idx) => {{
                    const sel = '{INTERACTIVE_SELECTOR}';
                    const els = [...document.querySelectorAll(sel)].filter(el => {{
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight;
                    }});
                    if (idx >= els.length) return false;
                    els[idx].click();
                    return true;
                }}
            """, index)
            if not clicked:
                return {"success": False, "error": f"Index {index} out of range"}
            
            # Wait briefly for potential navigation
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=2000)
            except:
                pass  # No navigation occurred, continue
            
            return {"success": True, "index": index}
        except Exception as e:
            # Navigation errors during click are SUCCESS (means the click worked)
            if "Execution context was destroyed" in str(e):
                try:
                    await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
                    return {"success": True, "index": index, "note": "Navigation occurred"}
                except:
                    return {"success": True, "index": index, "note": "Click triggered navigation"}
            return {"success": False, "error": str(e)}
    
    async def type_into_element(self, index: int, text: str, timeout: int = 5000) -> Dict[str, Any]:
        """Click element by index to focus, then type text. Does NOT auto-submit."""
        try:
            focused = await self._page.evaluate(f"""
                (idx) => {{
                    const sel = '{INTERACTIVE_SELECTOR}';
                    const els = [...document.querySelectorAll(sel)].filter(el => {{
                        const r = el.getBoundingClientRect();
                        return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight;
                    }});
                    if (idx >= els.length) return false;
                    els[idx].focus();
                    els[idx].click();
                    return true;
                }}
            """, index)
            if not focused:
                return {"success": False, "error": f"Index {index} out of range"}
            await self._page.keyboard.type(text, delay=50)
            return {"success": True, "index": index, "text_length": len(text)}
        except Exception as e:
            # Navigation during typing is OK
            if "Execution context was destroyed" in str(e):
                return {"success": True, "index": index, "note": "Navigation during typing"}
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
    
    # Recovery methods for error handling
    
    async def go_back(self) -> Dict[str, Any]:
        """Navigate back in browser history."""
        try:
            await self._page.go_back(wait_until="domcontentloaded")
            return {"success": True, "url": self._page.url}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def recover_from_popup(self) -> Dict[str, Any]:
        """Dismiss any dialogs/alerts that might block interaction."""
        try:
            # Close any open dialogs
            self._page.on("dialog", lambda dialog: dialog.dismiss())
            return {"success": True, "message": "Dialog handler registered"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def recover_focus(self) -> Dict[str, Any]:
        """Refocus main page content (useful after popup/modal)."""
        try:
            # Click body to regain focus
            await self._page.evaluate("document.body.focus()")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
