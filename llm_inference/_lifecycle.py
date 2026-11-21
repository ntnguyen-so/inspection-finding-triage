"""Cancellation-safe helpers for completing provider-owned async cleanup."""
from __future__ import annotations

import asyncio
from collections.abc import Coroutine


async def finish_cleanup(action: Coroutine) -> bool:
    """Finish cleanup despite cancellation and report whether cancellation occurred."""
    task = asyncio.create_task(action)
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            cancelled = True
    task.result()
    return cancelled
