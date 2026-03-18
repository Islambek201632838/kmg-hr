import asyncio
from functools import partial

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None
_client: QdrantClient | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.embedding_model)
    return _model


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def _search_sync(query_vector: list[float], dept_filter, top_k: int, threshold: float) -> list:
    client = get_qdrant()
    return client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=dept_filter,
        limit=top_k,
        score_threshold=threshold,
    )


def _encode_sync(text: str) -> list[float]:
    return get_model().encode(text).tolist()


def _encode_batch_sync(texts: list[str]) -> list[list[float]]:
    return get_model().encode(texts).tolist()


async def search_vnd(query: str, department_id: int | None = None, top_k: int = 5) -> list[dict]:
    """
    Search Qdrant for relevant VND document chunks (non-blocking).
    1. Try filtered by department_scope
    2. Fallback to unfiltered if too few results
    """
    loop = asyncio.get_event_loop()

    # Encode query in thread pool (CPU-bound)
    vector = await loop.run_in_executor(None, _encode_sync, query)

    # Build department filter
    dept_filter = None
    if department_id is not None:
        dept_filter = Filter(
            should=[
                FieldCondition(key="department_scope", match=MatchValue(value=department_id)),
                FieldCondition(key="department_scope", match=MatchValue(value=str(department_id))),
            ]
        )

    # Search in thread pool (I/O-bound)
    results = await loop.run_in_executor(
        None, partial(_search_sync, vector, dept_filter, top_k, 0.3)
    )

    # Fallback without filter
    if len(results) < 3:
        results = await loop.run_in_executor(
            None, partial(_search_sync, vector, None, top_k, 0.2)
        )

    return [
        {
            "text": hit.payload.get("text", ""),
            "doc_title": hit.payload.get("title", ""),
            "doc_id": hit.payload.get("doc_id", ""),
            "doc_type": hit.payload.get("doc_type", ""),
            "score": hit.score,
        }
        for hit in results
    ]


async def encode_text(text: str) -> list[float]:
    """Encode a single text (non-blocking)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _encode_sync, text)


async def encode_texts(texts: list[str]) -> list[list[float]]:
    """Encode multiple texts (non-blocking)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _encode_batch_sync, texts)
