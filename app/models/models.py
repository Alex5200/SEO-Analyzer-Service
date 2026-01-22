from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional


class AnalyzeRequest(BaseModel):
    url: str | None = "https://habr.com/"
    @field_validator('url', mode='before')
    @classmethod
    def validate_and_normalize_url(cls, v: str) -> str:
        validated_url = HttpUrl(v)
        return str(validated_url)


class AnalyzeResponse(BaseModel):
    url: str = None
    title: Optional[str] = None
    count_element: int = 0
    meta_description: Optional[str] = None
    cached: bool = False

class ParseResult(BaseModel):
    title: str = None
    count_element: int = 0
    meta_description: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    detail: str
    url: str