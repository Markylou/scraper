from urllib.parse import urlparse


def normalize_pasted_urls(raw_text: str) -> tuple[list[str], list[str]]:
    seen: set[str] = set()
    urls: list[str] = []
    rejected: list[str] = []

    candidates = raw_text.replace(",", "\n").splitlines()
    for candidate in candidates:
        value = candidate.strip()
        if not value:
            continue

        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            rejected.append(value)
            continue

        normalized = value.rstrip()
        if normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)

    return urls, rejected


def classify_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path
    if host == "finalfantasy.fandom.com" and path.startswith("/wiki/"):
        return "fandom"
    return "general"
