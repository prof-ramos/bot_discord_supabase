from functools import lru_cache
from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_supabase_client(url: str, key: str) -> Client:
    return create_client(url, key)
