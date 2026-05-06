from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Any


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ApiError(BaseModel):
    ok: bool = False
    error: ErrorDetail


class ApiSuccess(BaseModel):
    ok: bool = True
    data: Any
    meta: dict | None = None


# Input models
class SavePagesRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    urlsText: str = ""


class CreateJobRequest(BaseModel):
    sourceUrl: str
    maxDepth: int = 2
    sameDomainOnly: bool = True
    stayUnderStartPath: bool = True
    includeImages: bool = True
    includeDocuments: bool = True
    includeVideo: bool = False


class AddPagesRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)
    urlsText: str = ""