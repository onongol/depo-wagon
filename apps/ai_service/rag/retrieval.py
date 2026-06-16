from asgiref.sync import sync_to_async
from flashrank import Ranker, RerankRequest

TOP_K = 8
TOP_K_CANDIDATES = 20  # fetch more from pgvector, then rerank down to TOP_K
MAX_DISTANCE = 0.4  # cosine distance threshold: 0=identical, 1=opposite

# Loaded once at module level — model stays in memory across requests
ranker = Ranker(model_name="ms-marco-MultiBERT-L-12")


@sync_to_async
def fetch_similar_chunks(
    query_embedding: list[float],
    query_text: str,
    top_k: int = TOP_K,
) -> list[str]:
    """Two-stage retrieval: pgvector ANN search → FlashRank cross-encoder rerank."""
    from pgvector.django import CosineDistance

    from apps.ai_service.constants import DocumentStatus
    from apps.ai_service.models import DocumentChunk

    candidates = list(
        DocumentChunk.objects.filter(document__status=DocumentStatus.READY)
        .annotate(distance=CosineDistance("embedding", query_embedding))
        .filter(distance__lte=MAX_DISTANCE)
        .order_by("distance")
        .values_list("content", flat=True)[:TOP_K_CANDIDATES]
    )

    if not candidates:
        return []

    passages = [{"id": i, "text": text} for i, text in enumerate(candidates)]
    results = ranker.rerank(RerankRequest(query=query_text, passages=passages))

    return [r["text"] for r in results[:top_k]]
