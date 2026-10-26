import asyncio

from flashrank import RerankRequest

from apps.ai_service.rag.retrieval.config import get_ranker


def _rerank(query_text: str, candidates: list[dict], top_k: int) -> list[dict]:
    passages = [{"id": i, "text": c["content"]} for i, c in enumerate(candidates)]
    results = get_ranker().rerank(RerankRequest(query=query_text, passages=passages))
    return [candidates[r["id"]] for r in results[:top_k]]


async def rerank(query_text: str, candidates: list[dict], top_k: int) -> list[dict]:
    """Off sync_to_async's one thread, which every ORM call in the bot queues on."""
    if not candidates:
        return []
    return await asyncio.to_thread(_rerank, query_text, candidates, top_k)
