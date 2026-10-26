from asgiref.sync import sync_to_async

from apps.ai_service.rag.retrieval.config import MAX_DISTANCE, TOP_K_CANDIDATES
from apps.ai_service.rag.retrieval.rerank import rerank

TOP_K = 8


@sync_to_async
def _candidates(query_embedding: list[float]) -> list[dict]:
    from pgvector.django import CosineDistance

    from apps.ai_service.constants import DocumentStatus
    from apps.ai_service.models import DocumentChunk

    return list(
        DocumentChunk.objects.filter(document__status=DocumentStatus.READY)
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .filter(distance__lte=MAX_DISTANCE)
        .order_by("distance")
        .values("content", "document__title", "page_number")[:TOP_K_CANDIDATES]
    )


async def fetch_similar_chunks(
    query_embedding: list[float],
    query_text: str,
    top_k: int = TOP_K,
) -> list[dict]:
    candidates = await _candidates(query_embedding)
    return await rerank(query_text, candidates, top_k)
