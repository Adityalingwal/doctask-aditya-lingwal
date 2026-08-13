FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY . .
RUN pip install --no-cache-dir -e .

CMD ["sh", "-c", "exec uvicorn app.main:app --host ${APP_HOST:-127.0.0.1} --port 8000"]
