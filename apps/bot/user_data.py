from dataclasses import asdict, dataclass, field, fields
from typing import Any, Self

# Bump on a renamed field or a changed type. Adding or removing an optional one
# needs no bump: _known_fields and the defaults absorb both.
STATE_SCHEMA_VERSION = 1

_SCHEMA_KEY = "_schema"


def _known_fields(cls: type, data: dict[str, Any]) -> dict[str, Any]:
    """Drop keys the dataclass no longer declares, so stored state survives a deploy."""
    declared = {f.name for f in fields(cls)}
    return {k: v for k, v in data.items() if k in declared}


def _stamped(data: dict[str, Any]) -> dict[str, Any]:
    return data | {_SCHEMA_KEY: STATE_SCHEMA_VERSION}


def is_current_schema(data: dict[str, Any]) -> bool:
    """Whether a stored blob was written by this build's dataclasses."""
    return data.get(_SCHEMA_KEY) == STATE_SCHEMA_VERSION


@dataclass(frozen=True)
class EmployeeRef:
    """The three Employee attributes the responsible-employee flow reads."""

    id: int
    first_name: str = ""
    last_name: str = ""

    @classmethod
    def from_employee(cls, employee: Any) -> Self:
        return cls(
            id=employee.id,
            first_name=employee.first_name or "",
            last_name=employee.last_name or "",
        )

    def to_dict(self) -> dict[str, Any]:
        return _stamped(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self | None:
        """None for a blob another schema wrote: it is discarded, not migrated."""
        if not is_current_schema(data):
            return None
        return cls(**_known_fields(cls, data))


@dataclass
class AIResult:
    defect_class: str = ""
    confidence: float | None = None
    rag_recommendation: str = ""
    verdict: str = ""
    sources: list[str] = field(default_factory=list)


@dataclass
class MeasurementEntry:
    dimension: str = ""
    dimension_label: str = ""
    value: float | None = None
    norm_value: float | None = None
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Unstamped: only ever nested in DefectData, whose stamp covers it."""
        return cls(**_known_fields(cls, data))


@dataclass
class DefectData:
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
    severity_label: str | None = None
    description: str = ""
    measurements: list[MeasurementEntry] = field(default_factory=list)
    photo_file_ids: list[str] = field(default_factory=list)
    defect_id: str | None = None
    current_measurement: MeasurementEntry | None = None
    responsible_employee_id: int | None = None
    responsible_employee_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _stamped(asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self | None:
        """None for a blob another schema wrote: it is discarded, not migrated."""
        if not is_current_schema(data):
            return None

        raw = _known_fields(cls, data)
        raw["measurements"] = [
            MeasurementEntry.from_dict(m) for m in raw.get("measurements") or []
        ]
        current = raw.get("current_measurement")
        raw["current_measurement"] = (
            MeasurementEntry.from_dict(current) if current else None
        )
        return cls(**raw)
