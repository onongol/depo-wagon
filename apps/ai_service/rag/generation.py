from google import genai
from google.genai import types

from apps.ai_service.rag.config import GENERATION_MODEL, IMAGE_DESCRIPTION_PROMPT


async def describe_images(client: genai.Client, photos_bytes: list[bytes]) -> str:
    """Generate a short textual description of defect photos for query augmentation."""
    parts: list = []
    for photo in photos_bytes:
        parts.append(types.Part.from_bytes(data=photo, mime_type="image/jpeg"))
    parts.append(IMAGE_DESCRIPTION_PROMPT)
    response = await client.aio.models.generate_content(
        model=GENERATION_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=200),
    )
    return response.text or ""
