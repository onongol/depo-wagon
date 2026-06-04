from django.conf import settings
from google import genai
from google.genai import types

EMBEDDING_MODEL = "gemini-embedding-2"


def embed_text(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list[float]:
    """Embed text via gemini-embedding-2 (synchronous)."""
    client = genai.Client(api_key=settings.GOOGLE_AI_KEY)

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=3072
        ),
    )
    return list(response.embeddings[0].values)
