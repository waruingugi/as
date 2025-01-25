from typing import Callable

from django.core.cache import cache

from commons.constants import DEFAULT_CACHE_DURATION
from commons.logger import logger


# Analytics
class Analytics:
    """
    Parent class for analytics logic, providing shared utilities.
    """

    @staticmethod
    def get_cached_data(
        cache_key: str, fallback_fn: Callable, timeout: int = DEFAULT_CACHE_DURATION
    ):
        """
        Retrieve data from cache or compute and cache it using a fallback function.
        """
        try:
            logger.info(f"Fetching data for cache key: {cache_key}")
            data = cache.get(cache_key)
            if data is None:
                logger.info(f"Cache miss for key: {cache_key}. Computing data...")
                data = fallback_fn()
                cache.set(cache_key, data, timeout)
            return data
        except Exception as e:
            logger.error(f"Error fetching data for key {cache_key}: {e}")
            return fallback_fn()  # Safe default fallback
