from dataclasses import dataclass


@dataclass(frozen=True)
class NodeCB:
    value: str


@dataclass(frozen=True)
class DefectTypeCB:
    value: str


@dataclass(frozen=True)
class SeverityCB:
    value: str


@dataclass(frozen=True)
class PhotoSkipCB:
    pass


@dataclass(frozen=True)
class MeasurementAddCB:
    pass


@dataclass(frozen=True)
class MeasurementSkipCB:
    pass


@dataclass(frozen=True)
class MeasurementDoneCB:
    pass


@dataclass(frozen=True)
class DimensionCB:
    value: str


@dataclass(frozen=True)
class NormSkipCB:
    pass


@dataclass(frozen=True)
class UnitSkipCB:
    pass


@dataclass(frozen=True)
class DescSkipCB:
    pass


@dataclass(frozen=True)
class ConfirmCB:
    confirmed: bool


@dataclass(frozen=True)
class VerdictCB:
    value: str


@dataclass(frozen=True)
class TasksPageCB:
    page: int


@dataclass(frozen=True)
class StatusPickCB:
    defect_id: str
    page: int


@dataclass(frozen=True)
class StatusSetCB:
    defect_id: str
    status: str
    page: int
