from pathlib import Path
import sys
import asyncio


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ffxiii2_scraper.fetch_playwright import main


if __name__ == "__main__":
    asyncio.run(main())
