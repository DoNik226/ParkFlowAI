FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY back/pyproject.toml back/uv.lock ./back/
RUN pip install --no-cache-dir uv && \
    cd back && \
    uv sync --frozen --no-dev --no-install-project

COPY back ./back

EXPOSE 8000

CMD ["back/.venv/bin/python", "-m", "back.app.main"]