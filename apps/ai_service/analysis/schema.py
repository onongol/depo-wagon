from pydantic import BaseModel, Field


class FullAnalysisSchema(BaseModel):
    defect_class: str = Field(
        description="Precise technical defect classification per regulatory standards — single line."
    )
    confidence: float = Field(description="Confidence score from 0.00 to 1.00.")
    rag_recommendation: str = Field(
        description=(
            "Specific defect remediation recommendation (3–5 sentences). "
            "Use depot reference materials if provided, "
            "otherwise use general technical knowledge."
        )
    )
