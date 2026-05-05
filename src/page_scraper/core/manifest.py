from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path


def write_manifest(store, job_id: str) -> Path:
    job = store.get(job_id)
    output_root = Path(job["output_root"])
    pages = store.pages(job_id)
    assets = store.assets(job_id)
    failures = store.failures(job_id)
    manifest = {
        "app": "DL Tool",
        "version": "1.1-backend-no-sqlite",
        "sourceUrl": job["source_url"],
        "folderName": output_root.name,
        "status": job["status"],
        "createdAt": datetime.fromtimestamp(job["created_at"], UTC).isoformat(),
        "updatedAt": datetime.now(UTC).isoformat(),
        "settings": job.get("settings", {}),
        "summary": {
            "pagesDiscovered": len(pages),
            "pagesDownloaded": len([page for page in pages if page.get("status") == "downloaded"]),
            "assetsDiscovered": len(assets),
            "assetsDownloaded": len([asset for asset in assets if asset.get("status") == "downloaded"]),
            "failures": len(failures),
            "totalBytes": sum((page.get("size_bytes") or 0) for page in pages)
            + sum((asset.get("size_bytes") or 0) for asset in assets),
        },
        "downloadedPages": [page["local_path"] for page in pages if page.get("local_path")],
        "downloadedAssets": [asset["local_path"] for asset in assets if asset.get("local_path")],
        "failures": failures,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    store.event(job_id, "info", "manifest_written", "Manifest written", {"path": str(manifest_path)})
    return manifest_path
