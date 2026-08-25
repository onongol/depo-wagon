import time

from google.genai import types
from google.genai.errors import ClientError

from apps.ai_service.client import get_genai_client
from apps.ai_service.config import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL

BATCH_SIZE = 100
RETRY_DELAYS = [10, 30, 60]
RETRYABLE_HTTP_CODES = {429, 503, 504}


def embed_texts(
    texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT"
) -> list[list[float]]:
    """Embed a list of texts via gemini-embedding-2 (sync, with batching and retries)."""
    client = get_genai_client()

    config = types.EmbedContentConfig(
        task_type=task_type, output_dimensionality=EMBEDDING_DIMENSIONS
    )

    embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        contents = [
            types.Content(parts=[types.Part.from_text(text=text)]) for text in batch
        ]
        for attempt, delay in enumerate([0] + RETRY_DELAYS):
            if delay:
                time.sleep(delay)
            try:
                response = client.models.embed_content(
                    model=EMBEDDING_MODEL, contents=contents, config=config
                )
                break
            except ClientError as exc:
                if exc.code not in RETRYABLE_HTTP_CODES or attempt == len(RETRY_DELAYS):
                    raise
            except (ConnectionError, TimeoutError):
                if attempt == len(RETRY_DELAYS):
                    raise

        embeddings.extend(list(e.values) for e in response.embeddings)
    return embeddings
