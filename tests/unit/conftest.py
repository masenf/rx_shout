"""Shared fixtures for the rx_shout unit tests."""

import asyncio
from collections.abc import Callable, Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest


@pytest.fixture
def run_coro() -> Callable[[Coroutine[Any, Any, Any]], Any]:
    """Run a coroutine on a fresh event loop in a worker thread.

    When the integration tests run first, playwright's sync API leaves an
    asyncio loop marked running in the main thread for the whole session, so
    ``asyncio.run()`` cannot be called from test functions directly.
    """

    def _run(coro: Coroutine[Any, Any, Any]) -> Any:
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()

    return _run
