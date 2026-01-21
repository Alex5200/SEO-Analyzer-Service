from typing import Optional
from pydantic import BaseModel
from app.models.models import AnalyzeResponse
from app.logger import logger

class ParseResult(AnalyzeResponse):
    pass


class PageParser:
    REQUEST_TIMEOUT = 30000

    @classmethod
    async def analyze(cls, url: str, use_browser: bool = False) -> ParseResult:

        logger.debug(f"[PARSER] Начало анализа URL: {url}, use_browser={use_browser}")

        try:
            from playwright.async_api import async_playwright

            logger.debug("[PARSER] Инициализация Playwright...")
            async with async_playwright() as p:
                logger.debug("[PARSER] Playwright инициализирован")

                logger.debug("[PARSER] Запуск браузера Chromium...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ]
                )
                logger.debug("[PARSER] Браузер запущен успешно")

                try:
                    logger.debug("[PARSER] Создание новой страницы...")
                    page = await browser.new_page(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    )
                    is_react = await page.evaluate("typeof React !== 'undefined'")
                    is_vue = await page.evaluate("typeof Vue !== 'undefined'")
                    is_angular = await page.evaluate("typeof ng !== 'undefined'")

                    use_browser = is_react or is_vue or is_angular
                    logger.debug("[PARSER] Страница создана")

                    logger.debug(f"[PARSER] Переход на URL: {url} (timeout={cls.REQUEST_TIMEOUT}ms)")
                    await page.goto(
                        url, 
                        timeout=cls.REQUEST_TIMEOUT,
                        wait_until='domcontentloaded'
                    )
                    logger.debug("[PARSER] Страница загружена (domcontentloaded)")

                    if use_browser:
                        logger.debug("[PARSER] Ожидание загрузки динамического контента (networkidle)...")
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        logger.debug("[PARSER] Динамический контент загружен")

                    logger.debug("[PARSER] Извлечение title...")
                    title = await page.title()
                    title = title.strip() if title else None
                    logger.debug(f"[PARSER] Title получен: {title[:100] if title else 'None'}...")

                    logger.debug("[PARSER] Подсчёт элементов h1...")
                    h1_elements = await page.locator('h1').all()
                    h1_count = len(h1_elements)
                    logger.debug(f"[PARSER] Найдено h1 элементов: {h1_count}")

                    logger.debug("[PARSER] Извлечение meta description...")
                    meta_tag = page.locator('meta[name="description"]')
                    meta_description = None

                    meta_count = await meta_tag.count()
                    logger.debug(f"[PARSER] Найдено meta description тегов: {meta_count}")

                    if meta_count > 0:
                        meta_description = await meta_tag.first.get_attribute('content')
                        if meta_description:
                            meta_description = meta_description.strip() or None
                        logger.debug(f"[PARSER] Meta description: {meta_description[:100] if meta_description else 'None'}...")
                    else:
                        logger.debug("[PARSER] Meta description не найден")

                    result = ParseResult(
                        title=title,
                        h1_count=h1_count,
                        meta_description=meta_description
                    )
                    logger.debug(f"[PARSER] Анализ завершён успешно: {result}")
                    return result

                except Exception as e:
                    logger.error(f"[PARSER] Ошибка при работе со страницей: {type(e).__name__}: {str(e)}", exc_debug=True)
                    raise

                finally:
                    logger.debug("[PARSER] Закрытие браузера...")
                    await browser.close()
                    await page.close()
                    logger.debug("[PARSER] Браузер закрыт")

        except Exception as e:
            logger.error(f"[PARSER] Критическая ошибка в analyze: {type(e).__name__}: {str(e)}", exc_debug=True)
            raise