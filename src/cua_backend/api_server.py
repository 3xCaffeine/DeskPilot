"""
Local dev entry point — run the API server without Docker.

    cd src/cua_backend
    python api_server.py

In Docker, supervisord starts uvicorn directly (this file is not used).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("cua_backend.api.server:app", host="0.0.0.0", port=8000, reload=True)
