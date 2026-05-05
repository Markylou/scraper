from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse


SUPPORTED_SCHEMES = {"http", "https"}


def is_supported_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme.lower() in SUPPORTED_SCHEMES and bool(parsed.netloc)


def normalize_url(raw_url: str, base_url: str | None = None) -> str | None:
    value = (raw_url or "").strip()
    if not value:
        return None

    absolute = urljoin(base_url, value) if base_url else value
    parsed = urlparse(absolute)
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_SCHEMES or not parsed.netloc:
        return None

    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if not path.endswith("/") and "." not in path.rsplit("/", 1)[-1]:
        path = f"{path}/"
    query = urlencode(parse_qsl(parsed.query, keep_blank_values=True), doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def url_identity_key(url: str) -> str:
    normalized = normalize_url(url)
    return normalized or ""


def same_domain(url: str, root_url: str) -> bool:
    parsed = urlparse(normalize_url(url) or "")
    root = urlparse(normalize_url(root_url) or "")
    return parsed.netloc == root.netloc and bool(parsed.netloc)


def under_start_path(url: str, start_url: str) -> bool:
    parsed = urlparse(normalize_url(url) or "")
    start = urlparse(normalize_url(start_url) or "")
    if parsed.netloc != start.netloc:
        return False
    start_path = start.path if start.path.endswith("/") else f"{start.path}/"
    return parsed.path == start.path or parsed.path.startswith(start_path)
