from google.genai import types

from apps.ai_service.client import get_genai_client
from apps.ai_service.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


async def embed_query(text: str) -> list[float]:
    """Embed a query text via gemini-embedding-2 (async)."""
    response = await get_genai_client().aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY", output_dimensionality=EMBEDDING_DIMENSIONS
        ),
    )
    return list(response.embeddings[0].values)
