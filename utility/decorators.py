"""Decorators for async operations."""
import asyncio
from functools import wraps

import aiohttp


def retry_async(retries=3, delay=2, backoff=2, exceptions=(aiohttp.ClientError, asyncio.TimeoutError, asyncio.CancelledError)):
    """Decorator for retrying async functions with exponential backoff.
    
    Args:
        retries: Maximum number of attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _retries, _delay = retries, delay
            for attempt in range(_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt + 1 < _retries:
                        _delay *= backoff
                        await asyncio.sleep(_delay)
                    else:
                        raise
        return wrapper
    return decorator
