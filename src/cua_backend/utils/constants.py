"""Shared constants for browser element targeting."""

# Base CSS selector for interactive elements
INTERACTIVE_SELECTOR = (
    'a, button, input, select, textarea, '
    '[role="button"], [role="link"], [role="tab"], '
    '[role="option"], [role="menuitem"], [onclick]'
)

# Shared JS that builds allEls[] array of visible interactive DOM elements.
# Both browser_state.py and browser_controller.py MUST use this identical
# logic to guarantee element indices stay consistent.
FIND_ELEMENTS_JS = (
    "const _sel = '" + INTERACTIVE_SELECTOR + "';\n"
    """
    const _baseEls = document.querySelectorAll(_sel);
    const _seen = new WeakSet();
    const allEls = [];
    function _isVis(el) {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight;
    }
    function _addEl(el) {
        if (_seen.has(el)) return;
        if (!_isVis(el)) return;
        const _t = el.tagName;
        const _txt = (el.innerText || el.value || el.getAttribute('aria-label')
                       || el.getAttribute('placeholder') || el.title || '').trim();
        if (!_txt && _t !== 'INPUT' && _t !== 'TEXTAREA' && _t !== 'SELECT') return;
        _seen.add(el);
        allEls.push(el);
    }
    for (const el of _baseEls) { _addEl(el); }
"""
)
