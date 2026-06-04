from pydantic import BaseModel, Field

from apps.defects.constants import DefectVerdict


class FullAnalysisSchema(BaseModel):
    defect_class: str = Field(
        description="Точная техническая классификация дефекта по НТД — одна строка."
    )
    confidence: float = Field(description="Коэффициент уверенности от 0.00 до 1.00.")
    verdict: DefectVerdict = Field(
        description="Один из: ok, repair_soon, repair_now, decommission."
    )
    rag_recommendation: str = Field(
        description=(
            "Конкретная рекомендация по устранению дефекта (3–5 предложений). "
            "Опирайся на справочные материалы депо если они предоставлены, "
            "иначе используй общие технические знания."
        )
    )
