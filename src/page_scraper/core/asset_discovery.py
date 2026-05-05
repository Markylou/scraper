from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .normalizer import normalize_url, url_identity_key


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}


def extension_from_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if "." not in path.rsplit("/", 1)[-1]:
        return ""
    return "." + path.rsplit(".", 1)[-1]


def classify_asset_url(url: str) -> str:
    ext = extension_from_url(url)
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in DOCUMENT_EXTENSIONS:
        return "document"
    if ext in VIDEO_EXTENSIONS:
        return "video"
    if ext in AUDIO_EXTENSIONS:
        return "audio"
    return "other"


def parse_srcset(value: str) -> list[str]:
    urls: list[str] = []
    for item in value.split(","):
        candidate = item.strip().split(" ")[0].strip()
        if candidate:
            urls.append(candidate)
    return urls


def discover_assets(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    candidates: list[str] = []
    candidates.extend(
        value
        for value in (img.get("src") or img.get("data-src") for img in soup.select("img"))
        if value
    )
    for element in soup.select("[srcset]"):
        candidates.extend(parse_srcset(element.get("srcset") or ""))
    candidates.extend(
        href
        for href in (link.get("href") for link in soup.select("a[href]"))
        if href and classify_asset_url(urljoin(base_url, href)) != "other"
    )

    assets: dict[str, dict] = {}
    for candidate in candidates:
        normalized = normalize_url(candidate, base_url)
        if not normalized:
            continue
        asset_type = classify_asset_url(normalized)
        assets[url_identity_key(normalized)] = {
            "id": url_identity_key(normalized),
            "url": normalized,
            "asset_type": asset_type,
            "selected": True,
        }
    return list(assets.values())
