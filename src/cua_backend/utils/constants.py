"""Shared constants for browser element targeting."""

# Capture interactive elements + autocomplete/dropdown suggestions
INTERACTIVE_SELECTOR = '''
    a, button, input, select, textarea,
    [role="button"], [role="link"], [role="tab"], [role="option"], [role="menuitem"],
    [onclick],
    [role="listbox"] > *, [role="combobox"] > *,
    ul[role] li, ul[class*="suggest"] li, ul[class*="auto"] li, ul[class*="drop"] li,
    div[role="listbox"] > div, div[class*="suggest"] > div, div[class*="auto"] > div
'''.replace('\n', ' ').strip()
