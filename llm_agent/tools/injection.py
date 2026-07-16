"""Failure-injection seam

Three mechanisms, one injection point:

- error and delay are generic wrappers below - they copy any Tool, keeping
  its name and spec, so the model sees an identical tool list and cannot
  tell a sabotaged tool from a real one.
- conflicting or altered content is data, not a wrapper - pass canned data
  to the tool factory (weather_tool(conditions=...), web_search_tool(
  results=...)).
- the injection point is registry last-write-wins: registry.register(
  with_error(WEATHER, "...")) replaces the default tool under the same
  name. The agent loop and provider mocks are never touched.
"""

import asyncio
from dataclasses import replace

from .base import Tool


def with_error(tool: Tool, message: str) -> Tool:
    """Copy of the tool whose handler always raises; the loop turns every
    call into an error observation."""

    async def handler(**_args) -> str:
        raise RuntimeError(message)

    return replace(tool, handler=handler)


def with_delay(tool: Tool, seconds: float) -> Tool:
    """Copy of the tool that sleeps before delegating to the real handler.
    Composes: with_delay(with_error(...)) is a slow failure."""

    async def handler(**args) -> str:
        await asyncio.sleep(seconds)
        return await tool.handler(**args)

    return replace(tool, handler=handler)
