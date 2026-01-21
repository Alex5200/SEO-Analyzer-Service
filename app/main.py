from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from app.models.models import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from app.parser import PageParser
from app.cache import cache
from app.config import AppSettings
from app.logger import logger
from datetime import datetime
import logging

app = FastAPI(
    title="SEO Analyzer Service",
    description="Сервис для анализа веб-страниц и извлечения SEO-метаданных",
    version="1.0.0",
)
settings = AppSettings()

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    FastAPI middleware for logging requests.

    Logs the request method, path, status code, and duration of each request.
    """
    start_time = datetime.utcnow()

    response = await call_next(request)

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds() * 1000

    logger.info(
        f"{request.method} {request.url.path} — "
        f"Status: {response.status_code} — "
        f"Duration: {duration:.2f} ms"
    )

    return response


@app.get("/")
async def root():
    """
    Redirects to the API documentation page.

    Returns:
        RedirectResponse: redirect to /docs
    """
    return RedirectResponse(url="/docs")


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    summary="Анализ веб-страницы",
    description="""
    Анализирует веб-страницу по указанному URL и извлекает SEO-метаданные.
    
    Извлекаемые данные:
    - `title` — заголовок страницы из тега `<title>`
    - `h1_count` — количество тегов `<h1>` на странице
    - `meta_description` — содержимое `<meta name="description">`
    Параметры:
    - `url` — URL страницы (обязательно с http:// или https://) 
    Кеширование: результаты кешируются на 5 минут.
    """,
    responses={
        200: {
            "description": "Успешный анализ страницы",
            "content": {
                "application/json": {
                    "example": {
                        "url": "https://example.com",
                        "title": "Example Domain",
                        "h1_count": 1,
                        "meta_description": "This domain is for examples.",
                        "cached": False,
                    }
                }
            },
        },
        400: {"model": ErrorResponse, "description": "Невалидный URL"},
        502: {"model": ErrorResponse, "description": "Ошибка соединения с сайтом"},
        504: {"model": ErrorResponse, "description": "Таймаут при загрузке страницы"},
    },
    tags=["Анализ"],
)
async def analyze_page(request: AnalyzeRequest):
    """
    Анализирует веб-страницу по указанному URL и извлекает SEO-метаданные.

    Извлекаемые данные:
    - `title` — заголовок страницы из тега `<title>`
    - `h1_count` — количество тегов `<h1>` на странице
    - `meta_description` — содержимое `<meta name="description">`

    Параметры:
    - `url` — URL страницы (обязательно с http:// или https://)
    Кеширование: результаты кешируются на 5 минут.
    """
    url = request.url
    logging.info(f"Получен запрос: {url}")
    cache_key = f"{url}"
    cached_result = cache.get(cache_key)
    if cached_result:
        logging.info(f"Результат из кеша: {url}")
        return AnalyzeResponse(
            url=url,
            title=cached_result.get("title"),
            h1_count=cached_result.get("h1_count", 0),
            meta_description=cached_result.get("meta_description"),
            cached=True,
        )

    try:
        result = await PageParser.analyze(url)

        response_data = {
            "title": result.title,
            "h1_count": result.h1_count,
            "meta_description": result.meta_description,
        }

        cache.set(cache_key, response_data)
        logging.debug(f"Результат сохранён в кеш: {url}")

        return AnalyzeResponse(
            url=url,
            title=result.title,
            h1_count=result.h1_count,
            meta_description=result.meta_description,
            cached=False,
        )

    except Exception as e:
        error_msg = str(e)

        if "Timeout" in error_msg or "timeout" in error_msg:
            logging.warning(f"Таймаут: {url}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content=ErrorResponse(
                    error="timeout",
                    detail=f"Превышено время ожидания при загрузке {url}",
                    url=url,
                ).model_dump(),
            )

        if "net::ERR_" in error_msg or "Page.goto" in error_msg:
            logging.warning(f"Ошибка навигации: {url} - {error_msg}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content=ErrorResponse(
                    error="navigation_error",
                    detail=f"Не удалось загрузить страницу {url}: {error_msg}",
                    url=url,
                ).model_dump(),
            )

        logging.error(f"Неизвестная ошибка: {url} - {error_msg}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                error="unknown_error",
                detail=f"Ошибка при анализе {url}: {error_msg}",
                url=url,
            ).model_dump(),
        )


@app.delete("/api/cache")
async def clear_cache():
    """Очищает кэш. Возвращает сообщение об успешном удалении."""
    cache.clear()
    logging.info("Кеш очищен")
    return {"message": "Кеш очищен"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """
    Redirects to /docs if a 404 error occurs.

    Parameters
    ----------
    request : Request
        The request object
    exc : Exception
        The exception object

    Returns
    -------
    RedirectResponse
        A redirect response to /docs
    """
    logging.debug(f"404: {request.url.path} -> /docs")
    return RedirectResponse(url="/docs")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )