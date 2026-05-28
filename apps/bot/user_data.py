from dataclasses import dataclass, field


@dataclass
class RegData:
    email: str = ""


@dataclass
class AIResult:
    defect_class: str = ""
    confidence: float | None = None
    recommendation: str = ""
    verdict: str = ""


@dataclass
class MeasurementEntry:
    dimension: str = ""
    dimension_label: str = ""
    value: float | None = None
    norm_value: float | None = None
    unit: str = ""


@dataclass
class DefectData:
    wagon_id: int | None = None
    wagon_number: str | None = None
    node: str | None = None
    node_label: str | None = None
    defect_type: str | None = None
    defect_type_label: str | None = None
    severity: str | None = None
    severity_label: str | None = None
    description: str = ""
    measurements: list[MeasurementEntry] = field(default_factory=list)
    photo_file_ids: list[str] = field(default_factory=list)
    defect_id: str | None = None
    current_measurement: MeasurementEntry | None = None
