from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from page_scraper.content_builder import main


if __name__ == "__main__":
    result = main()
    print(f"Refreshed {len(result['rebuilt'])} page folder(s)")
    if result["skipped"]:
        print(f"Skipped {len(result['skipped'])} folder(s) without source.html")
