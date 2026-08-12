from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from app.startup import migrate_database, report_formats_without_readers


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_URL_ENVIRONMENT_VARIABLE = "DATABASE_URL"
FORMATS_CONFIG_PATH = PROJECT_ROOT / "config" / "formats.yaml"
AVAILABLE_READER_EXTENSIONS: frozenset[str] = frozenset()


def database_url_from_environment() -> str:
    database_url = os.environ.get(DATABASE_URL_ENVIRONMENT_VARIABLE)
    if database_url is None:
        raise RuntimeError(
            "DATABASE_URL is not set — set it to the PostgreSQL connection URL "
            "before starting the application."
        )
    return database_url


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    database_url = database_url_from_environment()
    await asyncio.to_thread(migrate_database, PROJECT_ROOT, database_url)
    await asyncio.to_thread(
        report_formats_without_readers,
        FORMATS_CONFIG_PATH,
        AVAILABLE_READER_EXTENSIONS,
    )
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}
