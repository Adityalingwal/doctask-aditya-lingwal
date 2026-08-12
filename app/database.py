from __future__ import annotations

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


SQLALCHEMY_DRIVER_SUFFIX = "+psycopg"


def libpq_connection_string(database_url: str) -> str:
    """Turn the SQLAlchemy URL the application is configured with into the
    plain libpq string psycopg and the LangGraph checkpointer both take."""
    scheme, separator, rest = database_url.partition("://")
    return f"{scheme.replace(SQLALCHEMY_DRIVER_SUFFIX, '')}{separator}{rest}"


def build_connection_pool(database_url: str) -> AsyncConnectionPool:
    return AsyncConnectionPool(
        conninfo=libpq_connection_string(database_url),
        open=False,
        kwargs={
            # The LangGraph Postgres checkpointer requires both of these on
            # every connection it is handed.
            "autocommit": True,
            "row_factory": dict_row,
        },
    )
