from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from time import time
from uuid import uuid4


@dataclass
class Job:
    id: str
    type: str
    status: str = "running"
    messages: list[str] = field(default_factory=list)
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time)


class JobStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[str, Job] = {}

    def create(self, job_type: str) -> str:
        job_id = uuid4().hex
        with self._lock:
            self._jobs[job_id] = Job(id=job_id, type=job_type)
        return job_id

    def log(self, job_id: str, message: str) -> None:
        with self._lock:
            self._jobs[job_id].messages.append(message)

    def finish(self, job_id: str, result: dict) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "done"
            job.result = result

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "error"
            job.error = error

    def get(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs[job_id]
            return {
                "id": job.id,
                "type": job.type,
                "status": job.status,
                "messages": list(job.messages),
                "result": job.result,
                "error": job.error,
                "created_at": job.created_at,
            }
