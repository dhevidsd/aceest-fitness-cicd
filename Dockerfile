# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Python module that exposes create_app(); selects which application version is packaged.
ARG APP_MODULE=ACEest_Fitness

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_MODULE=${APP_MODULE}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health')"

CMD exec gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile - "${APP_MODULE}:create_app()"
