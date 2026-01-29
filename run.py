import sys
from pathlib import Path

# Add src to Python path so imports work
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Import and run the main function
from cua_backend.app.main import main

if __name__ == "__main__":
    main()
