from dataclasses import dataclass, field


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
