Структура проекта

1. Dockerfile - основной Dockerfile проекта
2. requirements.txt - список зависимостей
3. .gitignore - .gitignore
4. README.md - описание проекта
5. app/main.py - основной файл проекта
6. app/models.py - модели для pydantic
7. app/parser.py - логика парсинга HTML
8. app/cache.py - кеш с ttl

------------

# Запуск
# Сборка в докер
docker build -t seo-analyzer .

## Запуск контейнера
docker run -p 8000:8000 seo-analyzer