"""
browser_state.py - Chrome CDP State Extractor
==============================================
Extracts page state from Chrome via CDP (Chrome DevTools Protocol).
Gives agent "browser vision" - URL, focused elements, forms, etc.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Page


@dataclass
class BrowserState:
    """Current state of the browser page."""
    url: str
    title: str
    is_loading: bool
    focused_element: Optional[dict] = None  # {tag, id, class, value, type}
    visible_text: str = ""  # Main content text
    forms: List[dict] = None  # Detected forms with inputs
    
    def __post_init__(self):
        if self.forms is None:
            self.forms = []


class BrowserStateProvider:
    """Connects to Chrome via CDP and extracts page state."""
    
    def __init__(self, cdp_url: str = "http://127.0.0.1:9222"):
        self.cdp_url = cdp_url
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
    
    async def connect(self, retries: int = 5, delay: float = 1.0) -> bool:
        """
        Connect to Chrome via CDP with retry logic.
        
        Args:
            retries: Number of connection attempts
            delay: Initial delay between retries (doubles each time)
        """
        last_error = None
        
        for attempt in range(retries):
            try:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
                
                # Get the first page (active tab)
                contexts = self._browser.contexts
                if contexts and contexts[0].pages:
                    self._page = contexts[0].pages[0]
                    print(f"✅ CDP connected on attempt {attempt + 1}")
                    return True
                    
                # Browser connected but no pages - might need to wait
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                    continue
                    
                return False
                
            except Exception as e:
                last_error = e
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                    delay *= 2
                else:
                    print(f"CDP connection failed after {retries} attempts: {e}")
                    return False
        
        return False
    
    async def get_state(self) -> Optional[BrowserState]:
        """Extract current page state."""
        if not self._page:
            return None
        
        try:
            # Get basic page info
            url = self._page.url
            title = await self._page.title()
            
            # Check if page is loading
            is_loading = await self._page.evaluate("document.readyState !== 'complete'")
            
            # Get focused element
            focused = await self._get_focused_element()
            
            # Get visible text (simplified - just body text)
            visible_text = await self._page.evaluate("document.body.innerText || ''")
            
            # Get forms
            forms = await self._get_forms()
            
            return BrowserState(
                url=url,
                title=title,
                is_loading=is_loading,
                focused_element=focused,
                visible_text=visible_text[:1000],  # Limit text
                forms=forms
            )
        except Exception as e:
            print(f"Failed to get browser state: {e}")
            return None
    
    async def _get_focused_element(self) -> Optional[dict]:
        """Get currently focused element info."""
        try:
            result = await self._page.evaluate("""
                () => {
                    const el = document.activeElement;
                    if (!el || el.tagName === 'BODY') return null;
                    return {
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        class: el.className || null,
                        type: el.type || null,
                        value: el.value || null,
                        placeholder: el.placeholder || null
                    };
                }
            """)
            return result
        except:
            return None
    
    async def _get_forms(self) -> List[dict]:
        """Get all forms on the page."""
        try:
            forms = await self._page.evaluate("""
                () => {
                    return Array.from(document.forms).map(form => ({
                        id: form.id || null,
                        action: form.action || null,
                        inputs: Array.from(form.elements).map(el => ({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || null,
                            name: el.name || null,
                            id: el.id || null,
                            placeholder: el.placeholder || null
                        }))
                    }));
                }
            """)
            return forms
        except:
            return []
    
    async def is_on_search_engine(self) -> bool:
        """Detect if we're on a search engine."""
        if not self._page:
            return False
        url = self._page.url.lower()
        return any(engine in url for engine in ['google.com', 'bing.com', 'duckduckgo.com'])
    
    async def disconnect(self):
        """Clean up connection."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        self._page = None
        self._browser = None
        self._playwright = None
