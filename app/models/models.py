import re
from pydantic import BaseModel, HttpUrl, AnyUrl, field_validator, Field
from typing import Optional, List, Dict

class AnalyzeRequestContact(BaseModel):
    url: str | None = "https://buroremont.ru"
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Валидация URL с автоматическим добавлением протокола"""
        # Если нет протокола, добавляем https://
        if not v.startswith(('http://', 'https://')):
            v = f'https://{v}'

        # Простая проверка формата URL
        url_pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
        if not re.match(url_pattern, v):
            raise ValueError(f'Некорректный URL: {v}')

        return v


class AnalyzeResponseContact(BaseModel):
    url: str
    emails: list[str]
    phones: list[str]


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
    h1_count: int = 0
    meta_description: Optional[str] = None
    cached: bool = False


class ErrorResponse(BaseModel):
    error: str
    detail: str
    url: str


class ContactResult(BaseModel):
    """Результат поиска контактной информации."""
    url: str = Field(..., description="URL страницы, где производился поиск")
    emails: List[str] = Field(default_factory=list, description="Найденные email адреса")
    phones: List[str] = Field(default_factory=list, description="Найденные телефоны")
    found_on_main: bool = Field(..., description="Найдены ли контакты на главной странице")
