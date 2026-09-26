import os
import json
import logging

import finnhub
import redis
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_redis_client = None
_finnhub_client = None


def get_redis_client():
    """Lazy Redis client so import-time failures do not crash the app."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        _redis_client = redis.from_url(redis_url, socket_connect_timeout=2)
    return _redis_client


def get_finnhub_client():
    global _finnhub_client
    if _finnhub_client is None:
        _finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))
    return _finnhub_client


class _LazyProxy:
    """Allows both lazy real clients and unittest.mock.patch on these names."""

    def __init__(self, getter):
        self._getter = getter

    def __getattr__(self, name):
        return getattr(self._getter(), name)


redis_client = _LazyProxy(get_redis_client)
finnhub_client = _LazyProxy(get_finnhub_client)


def get_finnhub_quote(symbol):
    symbol = symbol.upper().strip()
    if not symbol:
        return None

    cache_key = f'stock:{symbol}'

    try:
        cached_price = redis_client.get(cache_key)
        if cached_price:
            logger.debug('CACHE HIT for %s', symbol)
            return json.loads(cached_price)
    except redis.exceptions.RedisError as e:
        logger.warning('Redis error on get for %s: %s', symbol, e)

    try:
        logger.debug('CACHE MISS / Finnhub quote for %s', symbol)
        quote = finnhub_client.quote(symbol)
        if quote and quote.get('c') is not None:
            try:
                redis_client.setex(cache_key, 60, json.dumps(quote))
            except redis.exceptions.RedisError as e:
                logger.warning('Redis error on set for %s: %s', symbol, e)
            return quote
    except Exception as e:
        logger.warning('Finnhub quote error for %s: %s', symbol, e)
    return None


def get_finnhub_profile(symbol):
    symbol = symbol.upper().strip()
    if not symbol:
        return None

    cache_key = f'profile:{symbol}'

    try:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            return json.loads(cached_data)
    except redis.exceptions.RedisError:
        pass

    try:
        profile = finnhub_client.company_profile2(symbol=symbol)
        if profile:
            try:
                redis_client.setex(cache_key, 86400, json.dumps(profile))
            except redis.exceptions.RedisError:
                pass
            return profile
    except Exception as e:
        logger.warning('Finnhub profile error for %s: %s', symbol, e)
    return None
