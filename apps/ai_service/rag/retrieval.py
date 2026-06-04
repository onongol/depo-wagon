from asgiref.sync import sync_to_async

from apps.ai_service.rag.config import TOP_K


@sync_to_async
def fetch_similar_chunks(query_embedding: list[float], top_k: int = TOP_K) -> list[str]:
    """Vector similarity search — returns top-K chunk texts from ready documents."""
    from pgvector.django import CosineDistance

    from apps.ai_service.constants import DocumentStatus
    from apps.ai_service.models import DocumentChunk

    return list(
        DocumentChunk.objects.filter(document__status=DocumentStatus.READY)
        .order_by(CosineDistance("embedding", query_embedding))
        .values_list("content", flat=True)[:top_k]
    )
