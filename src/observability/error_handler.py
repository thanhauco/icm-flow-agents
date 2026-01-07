"""Error handling helpers including an async retry decorator."""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 0.5,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator: retry an async function with exponential backoff."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base_delay
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - intentional broad retry
                    last_exc = exc
                    logger.warning(
                        "%s failed (attempt %d/%d): %s",
                        func.__name__,
                        attempt,
                        max_attempts,
                        exc,
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(delay)
                        delay *= 2
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


class ErrorHandler:
    """Collects and summarizes errors observed during processing."""

    def __init__(self) -> None:
        self._errors: list[str] = []

    def record(self, context: str, exc: Exception) -> None:
        message = f"{context}: {exc}"
        logger.error(message)
        self._errors.append(message)

    @property
    def errors(self) -> list[str]:
        return list(self._errors)

    def clear(self) -> None:
        self._errors.clear()
