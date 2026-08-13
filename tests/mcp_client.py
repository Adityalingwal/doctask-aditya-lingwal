from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_ENDPOINT_PATH = "/mcp/"


@dataclass(frozen=True)
class ToolAnswer:
    """What one MCP tool call returned, refusal and all."""

    refused: bool
    text: str
    payload: Any


def tool_names(base_url: str) -> list[str]:
    return asyncio.run(_tool_names(base_url))


def call_tool(base_url: str, name: str, arguments: dict[str, Any]) -> ToolAnswer:
    return asyncio.run(_call_tool(base_url, name, arguments))


@asynccontextmanager
async def _session(base_url: str) -> AsyncIterator[ClientSession]:
    """One MCP client session over the endpoint the application mounts."""
    url = base_url.rstrip("/") + MCP_ENDPOINT_PATH
    async with streamable_http_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def _tool_names(base_url: str) -> list[str]:
    async with _session(base_url) as session:
        listed = await session.list_tools()
    return sorted(tool.name for tool in listed.tools)


async def _call_tool(
    base_url: str,
    name: str,
    arguments: dict[str, Any],
) -> ToolAnswer:
    async with _session(base_url) as session:
        result = await session.call_tool(name, arguments)
    text = "\n".join(
        block.text for block in result.content if getattr(block, "text", None)
    )
    return ToolAnswer(
        refused=bool(result.isError),
        text=text,
        payload=(
            result.structuredContent
            if result.structuredContent is not None
            else _as_payload(text)
        ),
    )


def _as_payload(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text
