from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from app.config import AppSettings
from app.logger import logger
from app.routers.analyze import router as analyze_router
from datetime import datetime

app = FastAPI(
    title="SEO Analyzer Service",
    description="Сервис для анализа веб-страниц и извлечения SEO-метаданных",
    version="1.0.0",
)
settings = AppSettings()
app.include_router(analyze_router)

@app.middleware("http")
async def log_requests(request: Request, call_next) -> JSONResponse:
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
