import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache()
def get_supabase() -> Client:
    url = os.getenv('SUPABASE_URL') or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_ANON_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    if not url or not key:
        raise RuntimeError('Missing SUPABASE_URL and SUPABASE_KEY environment variables')
    return create_client(url, key)
