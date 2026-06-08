import os
import finnhub
import redis
import json
from dotenv import load_dotenv

load_dotenv()

redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

finnhub_client = finnhub.Client(api_key=os.getenv('FINNHUB_API_KEY'))

def get_finnhub_quote(symbol):
    symbol = symbol.upper()
    cache_key = f'stock:{symbol}'

    try:
        cached_price = redis_client.get(cache_key)
        if cached_price:
            print(f"✅ CACHE HIT PROFILE for {symbol}")
            return json.loads(cached_price)
    except redis.exceptions.RedisError as e:
        print(f"❌ REDIS ERROR: {e}")

    try:
        print(f"🌐 FETCHING PROFILE FROM FINNHUB FOR {symbol}...")
        quote = finnhub_client.quote(symbol)
        if quote and quote.get('c') is not None:
            try:
                redis_client.setex(cache_key, 60, json.dumps(quote))
            except redis.exceptions.RedisError as e:
                print(f"❌ REDIS SAVE ERROR: {e}")
            return quote
    except Exception as e:
        print(f"❌ FINNHUB ERROR: {e}")
    return None


def get_finnhub_profile(symbol):
    symbol = symbol.upper()
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
    except Exception:
        pass
    return None