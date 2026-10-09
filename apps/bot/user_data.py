from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

# Bump on a renamed field or a changed type.
STATE_SCHEMA_VERSION = 3

_SCHEMA_KEY = "_schema"


def is_current_schema(data: dict[str, Any]) -> bool:
    """Whether a stored blob was written by this build's models."""
    return data.get(_SCHEMA_KEY) == STATE_SCHEMA_VERSION


class _StampedModel(BaseModel):
    """A payload stored under its own key, so it carries the schema stamp."""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json") | {_SCHEMA_KEY: STATE_SCHEMA_VERSION}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self | None:
        """None for a blob another schema wrote: it is discarded, not migrated."""
        if not is_current_schema(data):
            return None
        return cls.model_validate(data)


class AIResult(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True, validate_assignment=True)

    defect_class: str = ""
    confidence: float | None = None
    rag_recommendation: str = ""
    verdict: str = ""
    sources: list[str] = Field(default_factory=list)


class MeasurementEntry(BaseModel):
    """Unstamped: only ever nested in DefectData, whose stamp covers it."""

    model_config = ConfigDict(extra="ignore", strict=True, validate_assignment=True)

    dimension: str = ""
    dimension_label: str = ""
    value: float | None = None
    unit: str = ""


class PhotoEntry(BaseModel):
    """Unstamped: only ever nested in DefectData, whose stamp covers it."""

    model_config = ConfigDict(extra="ignore", strict=True, validate_assignment=True)

    file_id: str
    message_id: int


class DefectData(_StampedModel):
    model_config = ConfigDict(extra="ignore", strict=True, validate_assignment=True)

    wagon_id: int | None = None
    wagon_number: str | None = None
    department: str | None = None
    department_label: str | None = None
    node: str | None = None
    node_label: str | None = None
    part_number: str = ""
    defect_type: str | None = None
    defect_type_label: str | None = None
    severity: str | None = None
    verdict: str | None = None
    description: str = ""
    measurements: list[MeasurementEntry] = Field(default_factory=list)
    photos: list[PhotoEntry] = Field(default_factory=list)
    defect_id: str | None = None
    current_measurement: MeasurementEntry | None = None
    responsible_employee_id: int | None = None
    responsible_employee_label: str | None = None
