import asyncio
from functools import partial

import google.generativeai as genai
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.config import settings

_client: QdrantClient | None = None
_genai_configured = False


def _ensure_genai():
    global _genai_configured
    if not _genai_configured:
        genai.configure(api_key=settings.gemini_api_key)
        _genai_configured = True


def get_qdrant() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def _embed_sync(text: str) -> list[float]:
    """Embed text via Gemini API (no torch, no GPU, ~100ms)."""
    _ensure_genai()
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_query",
    )
    return result["embedding"]


def _embed_batch_sync(texts: list[str]) -> list[list[float]]:
    """Batch embed via Gemini API."""
    _ensure_genai()
    results = []
    for text in texts:
        result = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_query",
        )
        results.append(result["embedding"])
    return results


def _search_sync(query_vector: list[float], dept_filter, top_k: int, threshold: float) -> list:
    client = get_qdrant()
    return client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=dept_filter,
        limit=top_k,
        score_threshold=threshold,
    )


async def search_vnd(query: str, department_id: int | None = None, top_k: int = 5) -> list[dict]:
    """
    Search Qdrant for relevant VND document chunks (non-blocking).
    Uses Gemini Embedding API instead of SentenceTransformer.
    1. Try filtered by department_scope
    2. Fallback to unfiltered if too few results
    """
    loop = asyncio.get_event_loop()

    # Encode query via Gemini Embedding API
    vector = await loop.run_in_executor(None, _embed_sync, query)

    # Build department filter
    dept_filter = None
    if department_id is not None:
        dept_filter = Filter(
            should=[
                FieldCondition(key="department_scope", match=MatchValue(value=department_id)),
                FieldCondition(key="department_scope", match=MatchValue(value=str(department_id))),
            ]
        )

    # Search in thread pool
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
    return await loop.run_in_executor(None, _embed_sync, text)


async def encode_texts(texts: list[str]) -> list[list[float]]:
    """Encode multiple texts (non-blocking)."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _embed_batch_sync, texts)