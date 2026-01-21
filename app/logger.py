# app/logger.py
import logging
import os
from pathlib import Path

# Путь к папке логов
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)  # создаёт папку, если не существует

# Полный путь к файлу
LOG_FILE = LOG_DIR / "app.log"

# Создаём форматтер
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Настраиваем файловый хендлер
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Настраиваем корневой логгер
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# Также можно добавить консольный вывод (опционально)
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)