from google import genai
from google.genai import types

from apps.ai_service.rag.config import EMBEDDING_MODEL


async def embed_query(client: genai.Client, text: str) -> list[float]:
    """Embed a query text via gemini-embedding-2 (async)."""
    response = await client.aio.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY", output_dimensionality=3072
        ),
    )
    return list(response.embeddings[0].values)
