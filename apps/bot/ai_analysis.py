import json
import logging

from pydantic import BaseModel, Field

from apps.bot.user_data import AIResult
from apps.defects.constants import DefectVerdict

logger = logging.getLogger(__name__)

VERDICT_CHOICES = list(DefectVerdict.values)

PROMPT_TEMPLATE = """
Ты — опытный инспектор по осмотру и техническому обслуживанию железнодорожных грузовых вагонов.
Твоя задача — проанализировать данные о выявленном дефекте и прикреплённые фотографии (если есть),
после чего выдать строгое техническое заключение.

Зафиксированный дефект:
- Узел/Элемент: {node}
- Тип дефекта: {defect_type}
- Степень критичности: {severity}
{description_line}

Пояснение к статусам вердикта:
- ok           = в пределах нормы (допуска), ремонт не требуется.
- repair_soon  = устранить при ближайшем плановом ремонте (деповском/капитальном).
- repair_now   = требуется текущий отцепочный ремонт (немедленное устранение).
- decommission = исключение вагона из инвентарного парка (списание/утилизация).
"""


class _DefectAnalysisSchema(BaseModel):
    defect_class: str = Field(
        description="Точная техническая классификация дефекта по НТД — одна строка."
    )
    confidence: float = Field(description="Коэффициент уверенности от 0.00 до 1.00.")
    recommendation: str = Field(
        description="Конкретные действия по устранению дефекта (3–4 предложения)."
    )
    verdict: str = Field(
        description="Один из: ok, repair_soon, repair_now, decommission."
    )


async def analyze_defect(
    node: str,
    defect_type: str,
    severity: str,
    description: str = "",
    photos_bytes: list[bytes] | None = None,
) -> AIResult:
    """Send defect info (+ optional photos) to Gemini and return structured result."""
    empty = AIResult()

    try:
        from django.conf import settings
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GOOGLE_AI_KEY)

        description_line = f"- Описание: {description}" if description else ""
        prompt = PROMPT_TEMPLATE.format(
            node=node,
            defect_type=defect_type,
            severity=severity,
            description_line=description_line,
        )

        contents: list = []
        for photo_bytes in photos_bytes or []:
            contents.append(
                types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg")
            )
        contents.append(prompt)

        response = await client.aio.models.generate_content(
            model="gemini-3.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=_DefectAnalysisSchema,
                temperature=0.1,
            ),
        )

        if not response.text:
            logger.warning("Gemini returned empty response")
            return empty

        return _parse_response(response.text)

    except Exception as exc:
        logger.error("AI analysis failed: %s", exc, exc_info=True)
        return empty


def _parse_response(text: str) -> AIResult:
    data = json.loads(text)
    result = AIResult()
    result.defect_class = data.get("defect_class", "")
    result.recommendation = data.get("recommendation", "")

    try:
        result.confidence = float(data.get("confidence", 0.0))
    except (ValueError, TypeError):
        pass

    verdict = str(data.get("verdict", "")).lower()
    if verdict in VERDICT_CHOICES:
        result.verdict = verdict

    return result
