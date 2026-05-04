from pathlib import Path


def load_urls(path: Path) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Could not find {path}")

    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

