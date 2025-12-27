from typing import Optional
from pydantic import BaseModel
import logging

logging.basicConfig(filename="py_parser.log", level=logging.INFO)

class ParseResult(BaseModel):
    title: Optional[str] = None
    h1_count: int = 0
    meta_description: Optional[str] = None


class PageParser:
    REQUEST_TIMEOUT = 30000

    @classmethod
    async def analyze(cls, url: str, use_browser: bool = False) -> ParseResult:
        
        logging.info(f"[PARSER] Начало анализа URL: {url}, use_browser={use_browser}")

        try:
            from playwright.async_api import async_playwright

            logging.info("[PARSER] Инициализация Playwright...")
            async with async_playwright() as p:
                logging.info("[PARSER] Playwright инициализирован")

                logging.info("[PARSER] Запуск браузера Chromium...")
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                    ]
                )
                logging.info("[PARSER] Браузер запущен успешно")

                try:
                    logging.info("[PARSER] Создание новой страницы...")
                    page = await browser.new_page(
                        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    )
                    is_react = await page.evaluate("typeof React !== 'undefined'")
                    is_vue = await page.evaluate("typeof Vue !== 'undefined'")
                    is_angular = await page.evaluate("typeof ng !== 'undefined'")

                    use_browser = is_react or is_vue or is_angular
                    logging.info("[PARSER] Страница создана")

                    logging.info(f"[PARSER] Переход на URL: {url} (timeout={cls.REQUEST_TIMEOUT}ms)")
                    await page.goto(
                        url, 
                        timeout=cls.REQUEST_TIMEOUT,
                        wait_until='domcontentloaded'
                    )
                    logging.info("[PARSER] Страница загружена (domcontentloaded)")

                    if use_browser:
                        logging.info("[PARSER] Ожидание загрузки динамического контента (networkidle)...")
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        logging.info("[PARSER] Динамический контент загружен")

                    logging.info("[PARSER] Извлечение title...")
                    title = await page.title()
                    title = title.strip() if title else None
                    logging.info(f"[PARSER] Title получен: {title[:100] if title else 'None'}...")

                    logging.info("[PARSER] Подсчёт элементов h1...")
                    h1_elements = await page.locator('h1').all()
                    h1_count = len(h1_elements)
                    logging.info(f"[PARSER] Найдено h1 элементов: {h1_count}")

                    logging.info("[PARSER] Извлечение meta description...")
                    meta_tag = page.locator('meta[name="description"]')
                    meta_description = None

                    meta_count = await meta_tag.count()
                    logging.info(f"[PARSER] Найдено meta description тегов: {meta_count}")

                    if meta_count > 0:
                        meta_description = await meta_tag.first.get_attribute('content')
                        if meta_description:
                            meta_description = meta_description.strip() or None
                        logging.info(f"[PARSER] Meta description: {meta_description[:100] if meta_description else 'None'}...")
                    else:
                        logging.info("[PARSER] Meta description не найден")

                    result = ParseResult(
                        title=title,
                        h1_count=h1_count,
                        meta_description=meta_description
                    )
                    logging.info(f"[PARSER] Анализ завершён успешно: {result}")
                    return result

                except Exception as e:
                    logging.error(f"[PARSER] Ошибка при работе со страницей: {type(e).__name__}: {str(e)}", exc_info=True)
                    raise

                finally:
                    logging.info("[PARSER] Закрытие браузера...")
                    await browser.close()
                    await page.close()
                    logging.info("[PARSER] Браузер закрыт")

        except Exception as e:
            logging.error(f"[PARSER] Критическая ошибка в analyze: {type(e).__name__}: {str(e)}", exc_info=True)
            raise