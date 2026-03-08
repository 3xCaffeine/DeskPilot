import sys
import os
from pathlib import Path

# Suppress Playwright Node.js warnings
os.environ["NODE_NO_WARNINGS"] = "1"

# Add 'src' directory to Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import and run the main function
from cua_backend.app.main import main

if __name__ == "__main__":
    main()
