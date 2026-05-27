"""
AI defect analysis using Google Gemini (google-genai SDK).

analyze_defect() is called after the defect is saved.
It returns a dict with: defect_class, confidence, recommendation, verdict.
"""

import logging

logger = logging.getLogger(__name__)

VERDICT_CHOICES = ("ok", "repair_soon", "repair_now", "decommission")

PROMPT_TEMPLATE = """
Та төмөр замын вагоны гэмтэл шинжилдэг мэргэжилтэн.

Бүртгэгдсэн гэмтлийн мэдээлэл:
- Зангилаа: {node}
- Гэмтлийн төрөл: {defect_type}
- Ноцтой байдал: {severity}
{description_line}

Дараах бүтэцтэйгээр, МОНГОЛ ХЭЛЭЭР хариулна уу:

АНГИЛАЛ: <гэмтлийн нарийн техник ангилал — нэг мөр>
ИТГЭЛЦЛЭЛ: <0.00–1.00 хооронд тоо>
ЗӨВЛӨМЖ: <засварын зөвлөмж — 1–2 өгүүлэл>
ДҮГНЭЛТ: <ok | repair_soon | repair_now | decommission>

Тайлбар:
- ok          = норм дотор, засвар шаардахгүй
- repair_soon = төлөвлөгөөт засвар хийх
- repair_now  = яаралтай засвар шаардлагатай
- decommission = вагоныг ашиглалтаас хасах
"""


async def analyze_defect(
    node: str,
    defect_type: str,
    severity: str,
    description: str = "",
    photos_bytes: list[bytes] | None = None,
) -> dict:
    """
    Send defect info (+ optional photo) to Gemini and return structured result.

    Returns:
        {
            "defect_class": str,
            "confidence": float | None,
            "recommendation": str,
            "verdict": str,          # one of VERDICT_CHOICES or ""
        }
    """
    empty = {
        "defect_class": "",
        "confidence": None,
        "recommendation": "",
        "verdict": "",
    }

    try:
        from django.conf import settings
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GOOGLE_AI_KEY)

        description_line = f"- Тайлбар: {description}" if description else ""
        prompt = PROMPT_TEMPLATE.format(
            node=node,
            defect_type=defect_type,
            severity=severity,
            description_line=description_line,
        )

        # Build contents: [all photos..., prompt text]
        contents: list = []
        for photo_bytes in (photos_bytes or []):
            contents.append(
                types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg")
            )
        contents.append(prompt)

        response = await client.aio.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
        )

        return _parse_response(response.text)

    except Exception as exc:
        logger.error("AI analysis failed: %s", exc, exc_info=True)
        return empty


def _parse_response(text: str) -> dict:
    """
    Parse the structured Gemini response into a dict.

    Expected format (each field on its own line):
        АНГИЛАЛ: ...
        ИТГЭЛЦЛЭЛ: 0.87
        ЗӨВЛӨМЖ: ...
        ДҮГНЭЛТ: repair_now
    """
    result = {
        "defect_class": "",
        "confidence": None,
        "recommendation": "",
        "verdict": "",
    }

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("АНГИЛАЛ:"):
            result["defect_class"] = line.split(":", 1)[1].strip()

        elif line.startswith("ИТГЭЛЦЛЭЛ:"):
            raw = line.split(":", 1)[1].strip()
            try:
                result["confidence"] = float(raw)
            except ValueError:
                pass

        elif line.startswith("ЗӨВЛӨМЖ:"):
            result["recommendation"] = line.split(":", 1)[1].strip()

        elif line.startswith("ДҮГНЭЛТ:"):
            raw = line.split(":", 1)[1].strip().lower()
            # Accept even if the model adds extra words
            for v in VERDICT_CHOICES:
                if v in raw:
                    result["verdict"] = v
                    break

    return result
