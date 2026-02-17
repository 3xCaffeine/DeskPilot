```mermaid
flowchart TD
     Start --> Observe
     Observe --> Decide
     Decide --> Execute
     Execute --> Verify
     Verify -->|Goal satisfied| Done
     Verify -->|Not satisfied| Escalate
     Escalate -->|Vision not used| VisionNavigator
     Escalate -->|Vision used| FailRetry
     VisionNavigator --> Execute
     FailRetry --> Observe

     subgraph Observe
          Observe --> TakeSS
          Observe --> ReadAX
          Observe --> AccessibilityState
          Observe --> WindowTitle
          Observe --> FocusActiveApp
          Observe --> BrowserCDP
          BrowserCDP --> URL
          BrowserCDP --> InteractiveElements
     end

     subgraph Decide
          Decide --> PlannerDSPy
          Decide --> TextState
          Decide --> BrowserElements
          Decide --> History
          Decide --> PriorityOrder
          PriorityOrder --> DesktopActions
          PriorityOrder --> BrowserActions
          PriorityOrder --> VisionFallback
     end

     subgraph Execute
          Execute --> DesktopKeyPress
          Execute --> DesktopType
          Execute --> DesktopWait
          Execute --> BrowserNavigate
          Execute --> BrowserClick
          Execute --> BrowserType
     end

     subgraph Verify
          VerifyChecks --> URLChanged
          VerifyChecks --> FocusChanged
          VerifyChecks --> TextPresent
          VerifyChecks --> GoalSatisfied
     end
```
└────┬───────────────┘
     ↓
(back to OBSERVE)
