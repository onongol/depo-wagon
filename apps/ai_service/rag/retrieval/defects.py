from asgiref.sync import sync_to_async
from flashrank import RerankRequest

from apps.ai_service.rag.retrieval.config import MAX_DISTANCE, TOP_K_CANDIDATES, ranker

TOP_K_DEFECTS = 3


@sync_to_async
def fetch_similar_defects(
    query_embedding: list[float],
    query_text: str,
    top_k: int = TOP_K_DEFECTS,
) -> list[str]:
    from pgvector.django import CosineDistance

    from apps.ai_service.models import DefectVector

    candidates = list(
        DefectVector.objects.annotate(
            distance=CosineDistance("embedding", query_embedding)
        )
        .filter(distance__lte=MAX_DISTANCE)
        .order_by("distance")
        .values_list("content", flat=True)[:TOP_K_CANDIDATES]
    )

    if not candidates:
        return []

    passages = [{"id": i, "text": text} for i, text in enumerate(candidates)]
    results = ranker.rerank(RerankRequest(query=query_text, passages=passages))

    return [r["text"] for r in results[:top_k]]
