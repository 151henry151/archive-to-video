#!/usr/bin/env python3
"""
Run the archive-to-video web UI server.
"""

import os
import sys
from pathlib import Path

# Ensure project root is on path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PORT = int(os.environ.get("PORT", "18765"))
HOST = os.environ.get("HOST", "0.0.0.0")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=os.environ.get("RELOAD", "0") == "1",
    )
