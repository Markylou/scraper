from __future__ import annotations

import json

from .page_archive import archive_page, title_from_html
from .paths import PAGES_DIR, ensure_project_dirs


def read_metadata(folder) -> dict:
    metadata_file = folder / "metadata.json"
    if not metadata_file.exists():
        return {}
    return json.loads(metadata_file.read_text(encoding="utf-8"))


def rebuild_page_content(pages_dir=PAGES_DIR) -> dict:
    ensure_project_dirs()
    rebuilt: list[str] = []
    skipped: list[str] = []

    for source_file in sorted(pages_dir.rglob("source.html")):
        folder = source_file.parent
        html = source_file.read_text(encoding="utf-8")
        metadata = read_metadata(folder)
        title = metadata.get("title") or title_from_html(html, folder.name)
        source_url = metadata.get("source_url") or metadata.get("final_url") or ""
        final_url = metadata.get("final_url") or source_url
        strategy = metadata.get("strategy") or "saved"

        archive_page(
            url=source_url,
            final_url=final_url,
            title=title,
            html=html,
            strategy=strategy,
            pages_dir=pages_dir,
            folder=folder,
        )
        rebuilt.append(folder.relative_to(pages_dir).as_posix())

    return {"ok": True, "rebuilt": rebuilt, "skipped": skipped}


def main() -> dict:
    return rebuild_page_content()
