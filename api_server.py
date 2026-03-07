"""Start the DeskPilot API server."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("cua_backend.api.server:app", host="0.0.0.0", port=8000, reload=True)
