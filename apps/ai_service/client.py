from functools import cache

from django.conf import settings
from google import genai


@cache
def get_genai_client() -> genai.Client:
    """Return a shared Gemini client, creating it once on first use."""
    return genai.Client(api_key=settings.GOOGLE_AI_KEY)
