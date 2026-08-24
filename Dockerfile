FROM node:24.15.0-alpine AS ui-build

WORKDIR /ui

COPY ui/package.json ui/package-lock.json ./
RUN npm ci
COPY ui/ ./
RUN npm run build


FROM python:3.12.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY . .
COPY --from=ui-build /ui/dist /workspace/ui/dist
# The dev extra carries the PDF writer the test fixtures and the corpus script
# need; this image is what `docker compose run --rm app pytest` runs in.
RUN pip install --no-cache-dir -e ".[dev]"

CMD ["sh", "-c", "exec uvicorn app.main:app --host ${APP_HOST:-127.0.0.1} --port 8000"]
