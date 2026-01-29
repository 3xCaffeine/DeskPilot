"""
main.py - Entry point for DeskPilot
"""

import sys
import argparse
from cua_backend.agent import Agent, Planner
from cua_backend.execution import DesktopController
from cua_backend.schemas.tasks import Task

def main():
    parser = argparse.ArgumentParser(description="DeskPilot CLI")
    parser.add_argument("goal", type=str, help="The task for the agent to perform")
    parser.add_argument("--model", type=str, default="gemini/gemini-2.5-flash", help="DSPy model to use")
    parser.add_argument("--max-steps", type=int, default=10, help="Max steps for the task")
    args = parser.parse_args()

    # 1. Initialize logic
    print(f"🤖 Initializing DeskPilot with model: {args.model}")
    
    planner = Planner()
    planner.configure(model=args.model)
    
    # 2. Setup Vision fallback
    vision_client = None
    if args.model.startswith("openrouter/"):
        from cua_backend.llm.openrouter_client import OpenRouterClient
        vision_client = OpenRouterClient(model=args.model)
    else:
        from cua_backend.llm.gemini_client import GeminiClient
        # Map the dspy model name to the regular gemini format if needed
        gemini_model = args.model.replace("gemini/", "")
        vision_client = GeminiClient(model=gemini_model)

    # Standard desktop controller (PyAutoGUI)
    controller = DesktopController()
    
    # 3. Create the Agent
    agent = Agent(
        planner=planner,
        executor=controller,
        vision_llm=vision_client,
        runs_dir="runs"
    )

    # 3. Create and Run Task
    task = Task(goal=args.goal, max_steps=args.max_steps)
    
    print(f"🚀 Starting task: {args.goal}")
    print("-" * 50)
    
    try:
        result = agent.run(task)
        
        print("-" * 50)
        if result.success:
            print(f"✅ TASK COMPLETE: {result.final_answer}")
        else:
            print(f"❌ TASK FAILED: {result.error}")
            
    except KeyboardInterrupt:
        print("\n🛑 Task cancelled by user.")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")

if __name__ == "__main__":
    main()
