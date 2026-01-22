from fastapi import APIRouter, status, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from app.services.parser import PageParser
from app.models.models import AnalyzeRequest, AnalyzeResponse, ErrorResponse
from app.services.cache import cache

from app.logger import logger

router = APIRouter(prefix="/api/analyze")


@router.post(
    "/",
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
                        "count_element": 1,
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
async def analyze_page(request: AnalyzeRequest, element: str) -> AnalyzeResponse:
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
    logger.info(f"Получен запрос: {url}")
    cache_key = f"{url}"
    cached_result = cache.get(f"{cache_key}:{element}")
    if cached_result:
        logger.info(f"Результат из кеша: {url}")
        return AnalyzeResponse(
            url=url,
            title=cached_result.get("title"),
            count_element=cached_result.get("count_element", 0),
            meta_description=cached_result.get("meta_description"),
            cached=True,
        )

    try:
        result = await PageParser.analyze(url,element_to_parce=element)

        response_data = {
            "title": result.title,
            "count_element": result.count_element,
            "meta_description": result.meta_description,
        }

        cache.set(f"{cache_key}:{element}", response_data)
        logger.debug(f"Результат сохранён в кеш: {url}")

        return AnalyzeResponse(
            url=url,
            title=result.title,
            count_element=result.count_element,
            meta_description=result.meta_description,
            cached=False,
        )

    except Exception as e:
        error_msg = str(e)

        if "Timeout" in error_msg or "timeout" in error_msg:
            logger.warning(f"Таймаут: {url}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content=ErrorResponse(
                    error="timeout",
                    detail=f"Превышено время ожидания при загрузке {url}",
                    url=url,
                ).model_dump(),
            )

        if "net::ERR_" in error_msg or "Page.goto" in error_msg:
            logger.warning(f"Ошибка навигации: {url} - {error_msg}")
            return JSONResponse(
                status_code=status.HTTP_502_BAD_GATEWAY,
                content=ErrorResponse(
                    error="navigation_error",
                    detail=f"Не удалось загрузить страницу {url}: {error_msg}",
                    url=url,
                ).model_dump(),
            )

        logger.error(f"Неизвестная ошибка: {url} - {error_msg}")
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content=ErrorResponse(
                error="unknown_error",
                detail=f"Ошибка при анализе {url}: {error_msg}",
                url=url,
            ).model_dump(),
        )
