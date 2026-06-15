from google.genai import types

from apps.ai_service.client import get_genai_client
from apps.ai_service.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


def embed_texts(
    texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """Embed a batch of texts via gemini-embedding-2 (synchronous, single API call)."""
    response = get_genai_client().models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=EMBEDDING_DIMENSIONS
        ),
    )
    return [list(e.values) for e in response.embeddings]
