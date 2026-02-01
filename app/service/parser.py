from typing import Optional
from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Browser, Page

from app.models.models import AnalyzeResponse
from app.logger.logger import logger


class ParseResult(AnalyzeResponse):
    """Результат парсинга страницы с SEO-метаданными."""
    pass


class BrowserConfig:
    """Конфигурация браузера для Playwright."""
    REQUEST_TIMEOUT = 30000
    NETWORKIDLE_TIMEOUT = 15000
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    LAUNCH_ARGS = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
    ]


class PageParser:
    """Парсер веб-страниц для извлечения SEO-метаданных."""

    @staticmethod
    async def _detect_spa_framework(page: Page) -> bool:
        """Определяет наличие SPA-фреймворков на странице.

        Args:
            page: Объект страницы Playwright

        Returns:
            True, если обнаружен React, Vue или Angular
        """
        logger.debug("[PARSER] Проверка наличия SPA-фреймворков...")

        checks = [
            "typeof React !== 'undefined'",
            "typeof Vue !== 'undefined'",
            "typeof ng !== 'undefined'"
        ]

        for check in checks:
            if await page.evaluate(check):
                logger.debug(f"[PARSER] Обнаружен SPA-фреймворк: {check}")
                return True

        return False

    @staticmethod
    async def _extract_metadata(page: Page) -> dict:
        """Извлекает метаданные со страницы.

        Args:
            page: Объект страницы Playwright

        Returns:
            Словарь с полями title, h1_count, meta_description
        """
        logger.debug("[PARSER] Извлечение метаданных...")

        # Извлечение title
        title = await page.title()
        title = title.strip() if title else None
        logger.debug(f"[PARSER] Title: {title[:100] if title else 'None'}...")

        # Подсчет h1
        h1_count = await page.locator('h1').count()
        logger.debug(f"[PARSER] Найдено h1: {h1_count}")

        # Извлечение meta description
        meta_description = None
        meta_tag = page.locator('meta[name="description"]')

        if await meta_tag.count() > 0:
            content = await meta_tag.first.get_attribute('content')
            meta_description = content.strip() if content else None
            logger.debug(f"[PARSER] Meta description: {meta_description[:100] if meta_description else 'None'}...")
        else:
            logger.debug("[PARSER] Meta description не найден")

        return {
            'title': title,
            'h1_count': h1_count,
            'meta_description': meta_description
        }

    @classmethod
    @asynccontextmanager
    async def _get_browser_page(cls):
        """Контекстный менеджер для управления жизненным циклом браузера.

        Yields:
            Page: Объект страницы Playwright
        """
        logger.debug("[PARSER] Инициализация Playwright...")

        async with async_playwright() as playwright:
            logger.debug("[PARSER] Запуск браузера Chromium...")

            browser = await playwright.chromium.launch(
                headless=True,
                args=BrowserConfig.LAUNCH_ARGS
            )

            try:
                logger.debug("[PARSER] Создание новой страницы...")
                page = await browser.new_page(user_agent=BrowserConfig.USER_AGENT)
                logger.debug("[PARSER] Страница создана")

                yield page

            finally:
                logger.debug("[PARSER] Закрытие браузера...")
                await browser.close()
                logger.debug("[PARSER] Браузер закрыт")

    @classmethod
    async def analyze(cls, url: str, use_browser: bool = False) -> ParseResult:
        """Анализирует веб-страницу и извлекает SEO-метаданные.

        Использует Playwright для загрузки страницы в headless-браузере.
        Автоматически определяет SPA-фреймворки (React, Vue, Angular) и ожидает
        загрузки динамического контента при их обнаружении.

        Args:
            url: URL для анализа (должен быть валидным и доступным)
            use_browser: Принудительное использование режима ожидания networkidle

        Returns:
            ParseResult с полями title, h1_count, meta_description

        Raises:
            Exception: При ошибках загрузки или парсинга страницы
        """
        logger.debug(f"[PARSER] Начало анализа URL: {url}, use_browser={use_browser}")

        try:
            async with cls._get_browser_page() as page:
                logger.debug(f"[PARSER] Переход на URL: {url}")

                await page.goto(
                    url,
                    timeout=BrowserConfig.REQUEST_TIMEOUT,
                    wait_until='domcontentloaded'
                )
                logger.debug("[PARSER] Страница загружена (domcontentloaded)")

                # Определение необходимости ожидания динамического контента
                is_spa = await cls._detect_spa_framework(page)
                should_wait = use_browser or is_spa

                if should_wait:
                    logger.debug("[PARSER] Ожидание networkidle...")
                    await page.wait_for_load_state(
                        'networkidle',
                        timeout=BrowserConfig.NETWORKIDLE_TIMEOUT
                    )
                    logger.debug("[PARSER] Динамический контент загружен")

                # Извлечение метаданных
                metadata = await cls._extract_metadata(page)

                result = ParseResult(**metadata)
                logger.debug(f"[PARSER] Анализ завершён: {result}")

                return result

        except Exception as e:
            logger.error(
                f"[PARSER] Ошибка при анализе {url}: {type(e).__name__}: {str(e)}",
                exc_debug=True
            )
            raise
