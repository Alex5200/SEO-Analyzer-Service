import re
from typing import Dict, List, Optional

from contextlib import asynccontextmanager
from playwright.async_api import async_playwright, Page

from app.models.models import AnalyzeResponse, ContactResult
from app.logger.logger import logger


class ParseResult(AnalyzeResponse):
    """Результат парсинга страницы с SEO-метаданными."""

    pass


class BrowserConfig:
    """Конфигурация браузера для Playwright."""

    REQUEST_TIMEOUT = 30000
    NETWORKIDLE_TIMEOUT = 15000
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    LAUNCH_ARGS = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
    ]


class PageParser:
    """Парсер веб-страниц для извлечения SEO-метаданных."""

    CAHE_GETCONTACT = {}
    # Регулярные выражения для поиска контактов
    EMAIL_PATTERN = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    # Улучшенный паттерн для телефонов - исключаем пустые совпадения
    PHONE_PATTERN = r"(?:\+7|8|7)[\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})"

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
            "typeof ng !== 'undefined'",
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
        h1_count = await page.locator("h1").count()
        logger.debug(f"[PARSER] Найдено h1: {h1_count}")

        # Извлечение meta description
        meta_description = None
        meta_tag = page.locator('meta[name="description"]')

        if await meta_tag.count() > 0:
            content = await meta_tag.first.get_attribute("content")
            meta_description = content.strip() if content else None
            logger.debug(
                f"[PARSER] Meta description: {meta_description[:100] if meta_description else 'None'}..."
            )
        else:
            logger.debug("[PARSER] Meta description не найден")

        return {
            "title": title,
            "h1_count": h1_count,
            "meta_description": meta_description,
        }

    @classmethod
    async def _find_contacts_on_page(cls, page: Page) -> Dict[str, List[str]]:
        """Ищет контактную информацию на текущей странице.

        Args:
            page: Объект страницы Playwright

        Returns:
            Словарь с ключами 'emails' и 'phones'
        """
        logger.debug("[PARSER] Поиск контактов на странице...")

        # Получаем весь текстовый контент страницы
        content = await page.content()

        # Поиск email
        emails = re.findall(cls.EMAIL_PATTERN, content)
        emails = list(set(emails))  # Удаляем дубликаты
        logger.debug(f"[PARSER] Найдено email: {len(emails)}")

        # Поиск телефонов с улучшенной обработкой
        phone_matches = re.findall(cls.PHONE_PATTERN, content)
        phones = []

        for match in phone_matches:
            # match будет кортежем из групп (xxx, xxx, xx, xx)
            if isinstance(match, tuple):
                # Форматируем телефон в читаемый вид
                phone = f"+7 ({match[0]}) {match[1]}-{match[2]}-{match[3]}"
                phones.append(phone)
            elif match:  # если это строка
                phones.append(match)

        phones = list(set(phones))  # Удаляем дубликаты
        # Фильтруем пустые строки и слишком короткие номера
        phones = [
            p
            for p in phones
            if p
            and len(p.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")) >= 10
        ]

        logger.debug(f"[PARSER] Найдено телефонов: {len(phones)}")

        return {"emails": emails, "phones": phones}

    @classmethod
    async def _find_contact_page_link(cls, page: Page) -> Optional[str]:
        """Ищет ссылку на страницу контактов.

        Args:
            page: Объект страницы Playwright

        Returns:
            URL страницы контактов или None
        """
        logger.debug("[PARSER] Поиск ссылки на страницу контактов...")

        # Варианты текста для поиска
        contact_keywords = [
            "контакты",
            "контакт",
            "contact",
            "contacts",
            "связаться",
            "связь",
            "о нас",
            "about",
        ]

        for keyword in contact_keywords:
            try:
                # Поиск по ссылкам
                link = page.get_by_role("link", name=re.compile(keyword, re.IGNORECASE))

                if await link.count() > 0:
                    href = await link.first.get_attribute("href")
                    if href:
                        logger.debug(f"[PARSER] Найдена ссылка на контакты: {href}")
                        return href
            except Exception as e:
                logger.debug(f"[PARSER] Ошибка при поиске по ключу '{keyword}': {e}")
                continue

        # Если не нашли по роли, пробуем просто по тексту
        try:
            link = page.get_by_text(re.compile(r"контакт|contact", re.IGNORECASE)).first
            if await link.count() > 0:
                href = await link.get_attribute("href")
                if href:
                    logger.debug(f"[PARSER] Найдена ссылка на контакты (по тексту): {href}")
                    return href
        except Exception as e:
            logger.debug(f"[PARSER] Не удалось найти ссылку по тексту: {e}")

        logger.debug("[PARSER] Ссылка на страницу контактов не найдена")
        return None

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
                headless=True, args=BrowserConfig.LAUNCH_ARGS
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
    async def getContact(cls, url: str, use_browser: bool = False) -> ContactResult:
        """Ищет контактную информацию на сайте.

        Сначала ищет на главной странице. Если не находит,
        пытается найти страницу контактов и ищет там.

        Args:
            url: URL для анализа
            use_browser: Принудительное использование режима ожидания networkidle

        Returns:
            ContactResult с найденными email и телефонами

        Raises:
            Exception: При ошибках загрузки или парсинга страницы
        """

        logger.info(f"[PARSER] Начало поиска контактов на URL: {url}")
        if url in cls.CAHE_GETCONTACT:
            logger.info(f"[PARSER] set cache {url} : {cls.CAHE_GETCONTACT}")
            return cls.CAHE_GETCONTACT[url]
        else:
            try:
                async with cls._get_browser_page() as page:
                    logger.info(f"[PARSER] Переход на URL: {url}")

                    await page.goto(
                        url,
                        timeout=BrowserConfig.REQUEST_TIMEOUT,
                        wait_until="domcontentloaded",
                    )
                    logger.info("[PARSER] Страница загружена")

                    # Проверка на SPA и ожидание при необходимости
                    is_spa = await cls._detect_spa_framework(page)
                    should_wait = use_browser or is_spa

                    if should_wait:
                        logger.info("[PARSER] Ожидание networkidle...")
                        await page.wait_for_load_state(
                            "networkidle", timeout=BrowserConfig.NETWORKIDLE_TIMEOUT
                        )

                    # Первая попытка поиска контактов на главной странице
                    contacts = await cls._find_contacts_on_page(page)
                    current_url = page.url

                    # Если контакты найдены, возвращаем результат
                    if contacts["emails"] or contacts["phones"]:
                        logger.info("[PARSER] Контакты найдены на главной странице")
                        result = ContactResult(
                            url=current_url,
                            emails=contacts["emails"],
                            phones=contacts["phones"],
                            found_on_main=True,
                        )
                        cls.CAHE_GETCONTACT[url] = result
                        logger.info(f"cache {url} : {cls.CAHE_GETCONTACT} ")
                        return result

                    # Если не найдены, ищем страницу контактов
                    logger.info("[PARSER] Контакты не найдены, ищем страницу контактов...")
                    contact_link = await cls._find_contact_page_link(page)

                    if contact_link:
                        # Переход на страницу контактов
                        logger.debug(f"[PARSER] Переход на страницу контактов: {contact_link}")

                        # Если ссылка относительная, делаем абсолютной
                        if not contact_link.startswith("http"):
                            from urllib.parse import urljoin

                            contact_link = urljoin(url, contact_link)

                        await page.goto(
                            contact_link,
                            timeout=BrowserConfig.REQUEST_TIMEOUT,
                            wait_until="domcontentloaded",
                        )
                        current_url = page.url

                        if should_wait:
                            await page.wait_for_load_state(
                                "networkidle", timeout=BrowserConfig.NETWORKIDLE_TIMEOUT
                            )

                        # Повторный поиск контактов
                        contacts = await cls._find_contacts_on_page(page)
                        logger.info("[PARSER] Поиск завершен на странице контактов")
                        result = ContactResult(
                            url=current_url,
                            emails=contacts["emails"],
                            phones=contacts["phones"],
                            found_on_main=False,
                        )
                        cls.CAHE_GETCONTACT[url] = result
                        return result
                    else:
                        logger.info("[PARSER] Страница контактов не найдена")
                        return ContactResult(
                            url=current_url, emails=[], phones=[], found_on_main=True
                        )

            except Exception as e:
                logger.error(
                    f"[PARSER] Ошибка при поиске контактов {url}: {type(e).__name__}: {str(e)}",
                    exc_debug=True,
                )
                return e

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
                    wait_until="domcontentloaded",
                )
                logger.debug("[PARSER] Страница загружена (domcontentloaded)")

                # Определение необходимости ожидания динамического контента
                is_spa = await cls._detect_spa_framework(page)
                should_wait = use_browser or is_spa

                if should_wait:
                    logger.debug("[PARSER] Ожидание networkidle...")
                    await page.wait_for_load_state(
                        "networkidle", timeout=BrowserConfig.NETWORKIDLE_TIMEOUT
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
                exc_info=True,
            )
            raise
