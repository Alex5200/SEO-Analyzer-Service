from typing import Optional
from pydantic import BaseModel
from app.models.models import AnalyzeResponse, ParseResult
from app.logger import logger



class PageParser:
    REQUEST_TIMEOUT = 30000

    @classmethod
    async def analyze(cls, url: str, use_browser: bool = False, element_to_parce: str = "h1") -> ParseResult:
        """Анализирует веб-страницу по заданному URL и извлекает ключевые SEO-метаданные.

        Метод использует Playwright для загрузки страницы в headless-браузере Chromium.
        Автоматически определяет наличие фреймворков React, Vue или Angular и при их обнаружении
        ожидает завершения загрузки динамического контента (состояние 'networkidle').
        Извлекает следующие данные:
        - заголовок страницы (<title>),
        - количество элементов <h1>,
        - содержимое мета-тега description.

        Args:
            url (str): Абсолютный URL веб-страницы для анализа. Должен быть валидным и доступным.
            use_browser (bool, optional): Флаг, принудительно включающий режим браузерной загрузки
                даже при отсутствии SPA-фреймворков. По умолчанию — False.
                Если на странице обнаружен React, Vue или Angular, режим включается автоматически.

        Returns:
            ParseResult: Объект с полями title (Optional[str]), h1_count (int),
            meta_description (Optional[str]).

        Raises:
            Exception: Любые исключения, возникающие при запуске браузера, загрузке страницы,
                таймаутах или ошибках выполнения JavaScript. Исключения логируются
                с уровнем ERROR и пробрасываются выше.

        Note:
            Таймаут загрузки страницы фиксирован (30 секунд), таймаут ожидания
            networkidle — 15 секунд. Браузер запускается в headless-режиме с аргументами,
            совместимыми с Docker-контейнерами.
        """
        logger.debug(f"[PARSER] Начало анализа URL: {url}, use_browser={use_browser}, element_to_parce={element_to_parce}")

        try:
            from playwright.async_api import async_playwright

            logger.debug("[PARSER] Инициализация Playwright...")
            async with async_playwright() as p:
                logger.debug("[PARSER] Playwright инициализирован")

                logger.debug("[PARSER] Запуск браузера Chromium...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--disable-images",
                        "--blink-settings=imagesEnabled=false",
                    ],
                )
                logger.debug("[PARSER] Браузер запущен успешно")

                try:
                    logger.debug("[PARSER] Создание новой страницы...")
                    page = await browser.new_page(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                    )
                    is_react = await page.evaluate("typeof React !== 'undefined'")
                    is_vue = await page.evaluate("typeof Vue !== 'undefined'")
                    is_angular = await page.evaluate("typeof ng !== 'undefined'")

                    use_browser = is_react or is_vue or is_angular
                    logger.debug("[PARSER] Страница создана")

                    logger.debug(
                        f"[PARSER] Переход на URL: {url} (timeout={cls.REQUEST_TIMEOUT}ms)"
                    )
                    await page.goto(
                        url, timeout=cls.REQUEST_TIMEOUT, wait_until="domcontentloaded"
                    )
                    logger.debug("[PARSER] Страница загружена (domcontentloaded)")

                    if use_browser:
                        logger.debug(
                            "[PARSER] Ожидание загрузки динамического контента (networkidle)..."
                        )
                        await page.wait_for_load_state("networkidle", timeout=15000)
                        logger.debug("[PARSER] Динамический контент загружен")

                    logger.debug("[PARSER] Извлечение title...")
                    title = await page.title()
                    title = title.strip() if title else None
                    logger.debug(
                        f"[PARSER] Title получен: {title[:100] if title else 'None'}..."
                    )

                    logger.debug("[PARSER] Подсчёт элементов h1...")
                    elements_to_parced = await page.locator(element_to_parce).all()
                    elements_to_parce_count = len(elements_to_parced)
                    logger.debug(f"[PARSER] Найдено {element_to_parce} элементов: {elements_to_parce_count}")

                    logger.debug("[PARSER] Извлечение meta description...")
                    meta_tag = page.locator('meta[name="description"]')
                    meta_description = None

                    meta_count = await meta_tag.count()
                    logger.debug(
                        f"[PARSER] Найдено meta description тегов: {meta_count}"
                    )

                    if meta_count > 0:
                        meta_description = await meta_tag.first.get_attribute("content")
                        if meta_description:
                            meta_description = meta_description.strip() or None
                        logger.debug(
                            f"[PARSER] Meta description: {meta_description[:100] if meta_description else 'None'}..."
                        )
                    else:
                        logger.debug("[PARSER] Meta description не найден")

                    result = ParseResult(
                        title=title,
                        count_element=elements_to_parce_count,
                        meta_description=meta_description,
                    )
                    logger.debug(f"[PARSER] Анализ завершён успешно: {result}")
                    return result

                except Exception as e:
                    logger.error(
                        f"[PARSER] Ошибка при работе со страницей: {type(e).__name__}: {str(e)}"
                    )
                    raise

                finally:
                    logger.debug("[PARSER] Закрытие браузера...")
                    await browser.close()
                    logger.debug("[PARSER] Браузер закрыт")

        except Exception as e:
            logger.error(
                f"[PARSER] Критическая ошибка в analyze: {type(e).__name__}: {str(e)}"
            )
            raise
