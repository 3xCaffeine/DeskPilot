┌──────────┐
│  START   │
└────┬─────┘
     ↓
┌────────────┐
│ OBSERVE    │
│ - Take SS  │  ← ALWAYS (logging only)
│ - Read AX  │  Accessibility state
│ - Window   │  title/focus/active app
│ - Browser  │  CDP state (if Chrome active)
│   • URL    │
│   • Interactive elements (indexed)
└────┬───────┘
     ↓
┌────────────────────┐
│ DECIDE_ACTION      │
│ (Planner - DSPy)   │
│                    │
│ Input:             │
│ - Text state       │
│ - Browser elements │
│ - History          │
│                    │
│ Priority order:    │
│ 1. Desktop actions │
│ 2. Browser actions │
│    (index-based)   │
│ 3. Vision fallback │
└────┬───────────────┘
     ↓
┌────────────────────┐
│ EXECUTE_ACTION     │
│ - Desktop:         │
│   • Key press      │
│   • Type           │
│   • Wait           │
│ - Browser (CDP):   │
│   • Navigate(url)  │
│   • Click(index)   │
│   • Type(index, text)│
└────┬───────────────┘
     ↓
┌────────────────────┐
│ VERIFY             │
│ - URL changed?     │
│ - Focus changed?   │
│ - Text present?    │
│ - Goal satisfied?  │
└────┬───────────────┘
     │
     ├── YES ───────────────▶ DONE
     │
     └── NO
          ↓
┌────────────────────┐
│ ESCALATE           │
│                    │
│ If not used vision │
│ → Vision Navigator │
│ Else → Fail/Retry  │
└────┬───────────────┘
     ↓
(back to OBSERVE)
