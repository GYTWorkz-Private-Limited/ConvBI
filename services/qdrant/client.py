import os
from qdrant_client import QdrantClient


def get_qdrant_client() -> QdrantClient:
    url = os.getenv("QDRANT_URL", "http://localhost:6333")
    api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=url, api_key=api_key)
    
    # Set sparse model for BM25
    client.set_sparse_model('Qdrant/bm25')
    
    return client

