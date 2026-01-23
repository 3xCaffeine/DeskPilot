from src.cua_backend.schemas.tasks import Task

class Agent:
    def __init__(self):
        pass

    def run_task(self, task: Task):
        print(f"Starting task: {task.name}")
        print(f"Description: {task.description}")
        print(f"Max steps: {task.max_steps}")
        # Placeholder for agent logic
        print("Agent execution started...")
