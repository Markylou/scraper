from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse, urlunparse

from bs4 import BeautifulSoup

from .normalizer import normalize_url, url_identity_key


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".avif"}
DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a"}
WIDTH_SUFFIX_RE = re.compile(r"-(\d+)w$", re.IGNORECASE)


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


def image_width_from_url(url: str) -> int | None:
    path = urlparse(url).path
    filename = path.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    match = WIDTH_SUFFIX_RE.search(stem)
    if not match:
        return None
    return int(match.group(1))


def image_variant_key(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path
    directory, filename = path.rsplit("/", 1) if "/" in path else ("", path)
    stem, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
    base_stem = WIDTH_SUFFIX_RE.sub("", stem)
    base_filename = f"{base_stem}.{ext.lower()}" if ext else base_stem
    base_path = f"{directory}/{base_filename}" if directory else base_filename
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), base_path, "", "", ""))


def image_variant_label(url: str) -> str:
    width = image_width_from_url(url)
    return f"{width}w" if width else "original"


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
        if asset_type == "image":
            key = image_variant_key(normalized)
            variant = {
                "url": normalized,
                "label": image_variant_label(normalized),
                "width": image_width_from_url(normalized),
                "occurrence_count": 1,
            }
            existing = assets.get(key)
            if existing:
                matching_variant = next((item for item in existing["variants"] if item["url"] == normalized), None)
                if matching_variant:
                    matching_variant["occurrence_count"] = matching_variant.get("occurrence_count", 1) + 1
                else:
                    existing["variants"].append(variant)
                existing["url"] = preferred_image_variant(existing["variants"])
                existing["selected_variant_url"] = existing["url"]
                existing["variant_count"] = len(existing["variants"])
                existing["occurrence_count"] = sum(item.get("occurrence_count", 1) for item in existing["variants"])
                continue
            assets[key] = {
                "id": key,
                "url": normalized,
                "asset_type": asset_type,
                "selected": True,
                "variant_group_id": key,
                "variants": [variant],
                "variant_count": 1,
                "occurrence_count": 1,
                "selected_variant_url": normalized,
            }
            continue

        assets[url_identity_key(normalized)] = {
            "id": url_identity_key(normalized),
            "url": normalized,
            "asset_type": asset_type,
            "selected": True,
            "variant_group_id": url_identity_key(normalized),
            "variants": [{"url": normalized, "label": "original", "width": None}],
            "variant_count": 1,
            "occurrence_count": 1,
            "selected_variant_url": normalized,
        }
    return list(assets.values())


def preferred_image_variant(variants: list[dict]) -> str:
    originals = [variant for variant in variants if variant.get("width") is None]
    if originals:
        return originals[0]["url"]
    return max(variants, key=lambda variant: variant.get("width") or 0)["url"]
