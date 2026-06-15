from google.genai import types

from apps.ai_service.client import get_genai_client
from apps.ai_service.config import GENERATION_MODEL
from apps.ai_service.rag.config import IMAGE_DESCRIPTION_PROMPT
from apps.ai_service.utils import mime_type_for_bytes


async def describe_images(photos_bytes: list[bytes]) -> str:
    """Generate a short textual description of defect photos for query augmentation."""
    parts: list[types.Part | str] = []
    for photo in photos_bytes:
        parts.append(
            types.Part.from_bytes(data=photo, mime_type=mime_type_for_bytes(photo))
        )
    parts.append(IMAGE_DESCRIPTION_PROMPT)

    response = await get_genai_client().aio.models.generate_content(
        model=GENERATION_MODEL,
        contents=parts,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=200),
    )
    return response.text or ""
