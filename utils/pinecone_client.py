import os
from functools import lru_cache


@lru_cache()
def get_pinecone():
    api_key = os.getenv('PINECONE_API_KEY')
    if not api_key:
        raise RuntimeError('Missing PINECONE_API_KEY environment variable')
    try:
        from pinecone import Pinecone
        pc = Pinecone(api_key=api_key)
        return pc
    except Exception as e:
        raise RuntimeError(f'Failed to initialize Pinecone: {e}')
