"""
browser_state.py - Chrome CDP State Extractor
==============================================
Extracts page state from Chrome via CDP (Chrome DevTools Protocol).
Gives agent "browser vision" - URL, focused elements, interactive elements, etc.
"""

from __future__ import annotations
import asyncio
from dataclasses import dataclass
from typing import Optional, List
from playwright.async_api import async_playwright, Browser, Page

from ..utils.constants import FIND_ELEMENTS_JS


@dataclass
class BrowserState:
    """Current state of the browser page."""
    url: str
    title: str
    is_loading: bool
    focused_element: Optional[dict] = None  # {tag, id, class, value, type}
    visible_text: str = ""  # Main content text
    interactive_elements: List[dict] = None  # Visible clickable elements with indices
    
    def __post_init__(self):
        if self.interactive_elements is None:
            self.interactive_elements = []
    
    def format_elements_for_llm(self) -> str:
        """Format interactive elements as a numbered list for the LLM."""
        if not self.interactive_elements:
            return "No interactive elements visible."
        
        close_keywords = ['close', 'dismiss', 'accept', 'got it', 'ok', '×', '✕', 'x']
        
        lines = []
        for el in self.interactive_elements:
            tag = el['tag'].upper()
            text = el['text'] or el['name'] or el['type'] or ''
            extra = f' -> {el["href"]}' if el['href'] else ''
            role = el.get('role', '')
            text_lower = text.lower().strip()
            
            # Detect dropdown suggestion items
            is_dropdown = role in ('option', 'menuitem')
            
            # Detect popup close buttons
            is_likely_close = (
                text_lower in close_keywords or 
                any(kw in text_lower for kw in ['close', 'dismiss', 'accept']) or
                text.strip() in ['×', '✕', 'X']
            )
            
            # Detect search/combobox inputs
            is_search_input = (
                tag in ['INPUT', 'TEXTAREA'] and
                (el.get('type') == 'search' or 
                 'search' in el.get('name', '').lower() or
                 'search' in text_lower or
                 role == 'combobox')
            )
            
            marker = ''
            if is_dropdown:
                marker = ' [DROPDOWN_OPTION]'
            elif is_likely_close:
                marker = ' [POPUP_CLOSER?]'
            elif is_search_input:
                marker = ' [SEARCH_INPUT]'
            
            lines.append(f'[{el["index"]}] <{tag}> "{text}"{extra}{marker}')
        return "\n".join(lines)


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
            
            # Get interactive elements
            interactive_elements = await self._get_interactive_elements()
            
            return BrowserState(
                url=url,
                title=title,
                is_loading=is_loading,
                focused_element=focused,
                visible_text=visible_text[:1000],  # Limit text
                interactive_elements=interactive_elements
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
    
    async def _get_interactive_elements(self) -> List[dict]:
        """Extract visible interactive elements in viewport with indices."""
        try:
            elements = await self._page.evaluate(
                "(() => {" + FIND_ELEMENTS_JS + """
                    return allEls.map((el, i) => ({
                        index: i,
                        tag: el.tagName.toLowerCase(),
                        role: el.getAttribute('role') || '',
                        text: (el.innerText || el.value || el.getAttribute('aria-label')
                              || el.getAttribute('placeholder') || el.title || '').trim().slice(0, 80),
                        type: el.type || '',
                        name: el.name || '',
                        href: el.href || ''
                    }));
                })()"""
            )
            return elements
        except Exception:
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
