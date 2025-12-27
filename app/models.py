from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional


class AnalyzeRequest(BaseModel):
    url: str

    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL должен начинаться с http:// или https://')
        return v


class AnalyzeResponse(BaseModel):
    url: str
    title: Optional[str] = None
    h1_count: int = 0
    meta_description: Optional[str] = None
    cached: bool = False


class ErrorResponse(BaseModel):
    error: str
    detail: str
    url: str