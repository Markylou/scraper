from __future__ import annotations

from urllib.parse import unquote, urlparse

from ..page_archive import page_slug_from_title
from ..paths import JOBS_DIR


def site_slug_from_url(source_url: str) -> str:
    parsed = urlparse(source_url)
    host = parsed.netloc.lower().split("@")[-1].split(":")[0]
    if host.startswith("www."):
        host = host[4:]
    labels = [label for label in host.split(".") if label]
    if len(labels) >= 2:
        return page_slug_from_title(labels[-2])
    if labels:
        return page_slug_from_title(labels[0])

    segments = [segment for segment in unquote(parsed.path).split("/") if segment]
    preferred = segments[0] if segments else "job"
    return page_slug_from_title(preferred)


def job_folder_name(source_url: str, job_id: str) -> str:
    return f"{site_slug_from_url(source_url)}_{job_id[:8]}"


def job_output_root(source_url: str, job_id: str, jobs_dir=JOBS_DIR):
    return jobs_dir / job_folder_name(source_url, job_id)
