from __future__ import annotations

from fastapi import Depends

from page_scraper.job_store import JobStore


# Global singleton for now (same pattern as before)
_job_store: JobStore | None = None


def get_job_store() -> JobStore:
    global _job_store
    if _job_store is None:
        _job_store = JobStore()
    return _job_store


def require_job(job_id: str, job_store: JobStore = Depends(get_job_store)):
    if not job_store.exists(job_id):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=404,
            detail={
                "ok": False,
                "error": {
                    "code": "job_not_found",
                    "message": "That job is no longer available. Start a new one and try again.",
                }
            },
        )
    return job_id