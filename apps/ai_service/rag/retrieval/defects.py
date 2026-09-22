from asgiref.sync import sync_to_async

from apps.ai_service.rag.retrieval.config import MAX_DISTANCE, TOP_K_CANDIDATES
from apps.ai_service.rag.retrieval.rerank import rerank

TOP_K_DEFECTS = 3


@sync_to_async
def _candidates(query_embedding: list[float]) -> list[dict]:
    from pgvector.django import CosineDistance

    from apps.ai_service.models import DefectVector

    return list(
        DefectVector.objects.annotate(
            distance=CosineDistance("embedding", query_embedding)
        )
        .filter(distance__lte=MAX_DISTANCE)
        .order_by("distance")
        .values("content", "created_at")[:TOP_K_CANDIDATES]
    )


async def fetch_similar_defects(
    query_embedding: list[float],
    query_text: str,
    top_k: int = TOP_K_DEFECTS,
) -> list[dict]:
    candidates = await _candidates(query_embedding)
    return await rerank(query_text, candidates, top_k)
