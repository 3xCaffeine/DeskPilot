import argparse
import yaml
import sys
from pathlib import Path
from src.cua_backend.schemas.tasks import Task
from src.cua_backend.agent.core import Agent

def load_task(task_path: str) -> Task:
    path = Path(task_path)
    if not path.exists():
        print(f"Error: Task file not found at {path}")
        sys.exit(1)
        
    with open(path, "r") as f:
        try:
            data = yaml.safe_load(f)
            return Task(**data)
        except yaml.YAMLError as e:
            print(f"Error parsing YAML: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"Error validating task: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="DeskPilot CLI")
    parser.add_argument("task_file", help="Path to the task YAML file")
    
    args = parser.parse_args()
    
    task = load_task(args.task_file)
    agent = Agent()
    agent.run_task(task)

if __name__ == "__main__":
    main()
