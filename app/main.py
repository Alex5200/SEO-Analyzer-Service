from fastapi import FastAPI, HTTPException, status, Request
from fastapi.responses import JSONResponse, RedirectResponse
from app.models import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from app.parser import PageParser
from app.cache import cache
import logging

app = FastAPI(
    title="SEO Analyzer Service",
    description="Сервис для анализа веб-страниц и извлечения SEO-метаданных",
    version="1.0.0",
)
logging.basicConfig(level=logging.INFO)

@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


@app.post(
    "/api/analyze",
    response_model=AnalyzeResponse,
    summary="Анализ веб-страницы",
    description="""
    Анализирует веб-страницу по указанному URL и извлекает SEO-метаданные.
    <br><br>
    Извлекаемые данные:<br> 
    - `title` — заголовок страницы из тега `<title>`<br> 
    - `h1_count` — количество тегов `<h1>` на странице<br> 
    - `meta_description` — содержимое `<meta name="description">`<br> 
    <br><br>
    Параметры:<br> 
    - `url` — URL страницы (обязательно с http:// или https://) <br> 
    <br><br>

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
                        "cached": False
                    }
                }
            }
        },
        400: {"model": ErrorResponse, "description": "Невалидный URL"},
        502: {"model": ErrorResponse, "description": "Ошибка соединения с сайтом"},
        504: {"model": ErrorResponse, "description": "Таймаут при загрузке страницы"},
    },
    tags=["Анализ"]
)
async def analyze_page(request: AnalyzeRequest):

    url = request.url
    
    logging.info(f"Получен запрос: {url}")
    
    cache_key = f"{url}"
    cached_result = cache.get(cache_key)
    
    if cached_result:
        logging.info(f"Результат из кеша: {url}")
        return AnalyzeResponse(
            url=url,
            title=cached_result.get('title'),
            h1_count=cached_result.get('h1_count', 0),
            meta_description=cached_result.get('meta_description'),
            cached=True
        )
    
    try:
        result = await PageParser.analyze(url)
        
        response_data = {
            'title': result.title,
            'h1_count': result.h1_count,
            'meta_description': result.meta_description
        }
        
        cache.set(cache_key, response_data)
        logging.debug(f"Результат сохранён в кеш: {url}")
        
        return AnalyzeResponse(
            url=url,
            title=result.title,
            h1_count=result.h1_count,
            meta_description=result.meta_description,
            cached=False
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
                    url=url
                ).model_dump()
            )
        
        if "net::ERR_" in error_msg or "Page.goto" in error_msg:
            logging.warning(f"Ошибка навигации: {url} - {error_msg}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content=ErrorResponse(
                    error="navigation_error",
                    detail=f"Не удалось загрузить страницу {url}: {error_msg}",
                    url=url
                ).model_dump()
            )
        
        logging.error(f"Неизвестная ошибка: {url} - {error_msg}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                error="unknown_error",
                detail=f"Ошибка при анализе {url}: {error_msg}",
                url=url
            ).model_dump()
        )


@app.delete("/api/cache")
async def clear_cache():
    cache.clear()
    logging.info("Кеш очищен")
    return {"message": "Кеш очищен"}


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logging.debug(f"404: {request.url.path} -> /docs")
    return RedirectResponse(url="/docs")