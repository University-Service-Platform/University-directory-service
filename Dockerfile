# University Directory Service
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8002 \
    DATABASE_URL=sqlite:////app/data/directory.db

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

RUN groupadd --system app && useradd --system --gid app --home-dir /app --no-create-home app

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini .

RUN mkdir -p /app/data && chown -R app:app /app/data
VOLUME ["/app/data"]

USER app

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8002\")}/health', timeout=4)" || exit 1

# Apply migrations, then serve. Configuration comes from the environment (see .env.example).
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
