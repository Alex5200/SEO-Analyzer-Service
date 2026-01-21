FROM mcr.microsoft.com/playwright/python:v1.49.1-noble

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000

CMD ["sh", "-c", "python -m uvicorn app.main:app --host $APP_HOST --port $APP_PORT"]