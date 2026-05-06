from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Ensure we can import page_scraper
os.environ.setdefault("PYTHONPATH", str(SRC))


def main() -> None:
    import uvicorn
    from page_scraper.api.app import app, main as app_main

    # Forward to the FastAPI main if it exists
    app_main()


if __name__ == "__main__":
    main()