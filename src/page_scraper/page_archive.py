from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from bs4.element import Comment, NavigableString, Tag

from .paths import PAGES_DIR


@dataclass(frozen=True)
class PageArchive:
    folder: Path
    source_file: Path
    content_html_file: Path
    markdown_file: Path
    metadata_file: Path


def clean_text(value: str | None) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def page_slug_from_title(title: str) -> str:
    value = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "page"


def title_from_html(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for selector in ["h1", "title"]:
        element = soup.select_one(selector)
        text = clean_text(element.get_text(" ", strip=True) if element else None)
        if text:
            return text
    return fallback


def page_folder_name(title: str, final_url: str) -> str:
    parsed = urlparse(final_url)
    path = unquote(parsed.path).strip("/")
    if path:
        if path.lower().endswith(".html"):
            path = path[:-5]
        return page_slug_from_title(path)
    return page_slug_from_title(title)


def url_path_segments(title: str, final_url: str) -> list[str]:
    parsed = urlparse(final_url)
    raw_segments = [segment for segment in unquote(parsed.path).split("/") if segment]
    segments: list[str] = []
    for segment in raw_segments:
        if segment.lower().endswith(".html"):
            segment = segment[:-5]
        slug = page_slug_from_title(segment)
        if slug:
            segments.append(slug)

    if not segments:
        segments = [page_slug_from_title(title)]

    if parsed.query:
        query_hash = hashlib.sha1(parsed.query.encode("utf-8")).hexdigest()[:8]
        segments[-1] = f"{segments[-1]}-{query_hash}"

    return segments


def page_folder_path(title: str, final_url: str, pages_dir: Path = PAGES_DIR) -> Path:
    folder = pages_dir
    for segment in url_path_segments(title, final_url):
        folder = folder / segment
    return folder


def select_content_root(soup: BeautifulSoup) -> Tag:
    selectors = [
        "main",
        "article",
        "#mw-content-text .mw-parser-output",
        ".mw-parser-output",
        ".page-content",
        ".content",
        "body",
    ]
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            return element
    return soup


def remove_page_chrome(content: Tag) -> None:
    selectors = [
        "script",
        "style",
        "noscript",
        "nav",
        "footer",
        "header",
        "aside",
        "form",
        ".toc",
        "#toc",
        ".mw-editsection",
        ".page-header__actions",
        ".portable-infobox",
        "aside.portable-infobox",
    ]
    for element in content.select(", ".join(selectors)):
        element.decompose()


def extract_content_html(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    content = select_content_root(soup)
    content_copy = BeautifulSoup(str(content), "lxml")
    root = content_copy.body or content_copy
    remove_page_chrome(root)
    inner = root.decode_contents().strip()
    return inner


def iter_direct_content(element: Tag):
    for child in element.children:
        if isinstance(child, Comment):
            continue
        if isinstance(child, NavigableString):
            text = clean_text(str(child))
            if text:
                yield text
        elif isinstance(child, Tag):
            yield child


def markdown_escape_cell(value: str) -> str:
    return value.replace("|", "\\|")


def table_to_markdown(table: Tag) -> str:
    rows: list[list[str]] = []
    for row in table.select("tr"):
        cells = [markdown_escape_cell(clean_text(cell.get_text(" ", strip=True))) for cell in row.select("th, td")]
        if cells:
            rows.append(cells)
    if not rows:
        return ""

    width = max(len(row) for row in rows)
    rows = [row + [""] * (width - len(row)) for row in rows]
    header = rows[0]
    divider = ["---"] * width
    body = rows[1:]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(divider) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in body)
    return "\n".join(lines)


def element_to_markdown(element) -> list[str]:
    if isinstance(element, str):
        return [element]
    if not isinstance(element, Tag):
        return []

    name = element.name or ""
    text = clean_text(element.get_text(" ", strip=True))

    if name in {"h1", "h2", "h3", "h4", "h5", "h6"} and text:
        level = int(name[1])
        return [f"{'#' * level} {text}"]
    if name == "p" and text:
        return [text]
    if name in {"ul", "ol"}:
        lines: list[str] = []
        ordered = name == "ol"
        for index, item in enumerate(element.find_all("li", recursive=False), start=1):
            item_text = clean_text(item.get_text(" ", strip=True))
            if item_text:
                prefix = f"{index}." if ordered else "-"
                lines.append(f"{prefix} {item_text}")
        return ["\n".join(lines)] if lines else []
    if name == "table":
        markdown = table_to_markdown(element)
        return [markdown] if markdown else []
    if name in {"blockquote"} and text:
        return ["\n".join(f"> {line}" for line in text.splitlines())]
    if name in {"pre"}:
        code = element.get_text("\n", strip=False).strip()
        return [f"```\n{code}\n```"] if code else []
    if name in {"div", "section", "main", "article", "body", "html"}:
        blocks: list[str] = []
        for child in iter_direct_content(element):
            blocks.extend(element_to_markdown(child))
        return blocks
    if text:
        return [text]
    return []


def content_markdown_from_html(content_html: str) -> str:
    soup = BeautifulSoup(content_html, "lxml")
    root = soup.body or soup
    blocks: list[str] = []
    for child in iter_direct_content(root):
        blocks.extend(element_to_markdown(child))
    return "\n\n".join(block for block in blocks if block).strip() + "\n"


def collect_urls(content_html: str, final_url: str) -> tuple[list[str], list[str]]:
    soup = BeautifulSoup(content_html, "lxml")
    images = [
        urljoin(final_url, src)
        for src in (clean_text(img.get("src") or img.get("data-src")) for img in soup.select("img"))
        if src
    ]
    links = [
        urljoin(final_url, href)
        for href in (clean_text(link.get("href")) for link in soup.select("a[href]"))
        if href
    ]
    return sorted(set(images)), sorted(set(links))


def archive_page(
    *,
    url: str,
    final_url: str,
    title: str,
    html: str,
    strategy: str,
    pages_dir: Path = PAGES_DIR,
    folder: Path | None = None,
) -> PageArchive:
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_title = title_from_html(html, title)
    page_folder = folder or page_folder_path(page_title, final_url, pages_dir)
    page_folder.mkdir(parents=True, exist_ok=True)

    source_file = page_folder / "source.html"
    content_html_file = page_folder / "content.html"
    markdown_file = page_folder / "content.md"
    metadata_file = page_folder / "metadata.json"

    content_html = extract_content_html(html)
    markdown = content_markdown_from_html(content_html)
    images, links = collect_urls(content_html, final_url)
    metadata = {
        "source_url": url,
        "final_url": final_url,
        "title": page_title,
        "slug": page_folder.name,
        "path": page_folder.relative_to(pages_dir).as_posix(),
        "saved_at": datetime.now(UTC).isoformat(),
        "strategy": strategy,
        "files": {
            "source_html": "source.html",
            "content_html": "content.html",
            "markdown": "content.md",
        },
        "images": images,
        "links": links,
    }

    source_file.write_text(html, encoding="utf-8")
    content_html_file.write_text(content_html, encoding="utf-8")
    markdown_file.write_text(markdown, encoding="utf-8")
    metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    return PageArchive(
        folder=page_folder,
        source_file=source_file,
        content_html_file=content_html_file,
        markdown_file=markdown_file,
        metadata_file=metadata_file,
    )
