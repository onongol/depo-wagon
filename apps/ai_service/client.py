from django.conf import settings
from google import genai

_client: genai.Client | None = None


def get_genai_client() -> genai.Client:
    """Return a shared Gemini client, creating it once on first use."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GOOGLE_AI_KEY)
    return _client
