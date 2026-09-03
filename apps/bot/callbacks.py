from dataclasses import dataclass


@dataclass(frozen=True)
class DepartmentCB:
    value: str


@dataclass(frozen=True)
class PartNumberSkipCB:
    pass


@dataclass(frozen=True)
class ResponsibleEmployeeCB:
    employee_id: int


@dataclass(frozen=True)
class ResponsibleEmployeeSkipCB:
    pass


@dataclass(frozen=True)
class ResponsibleEmployeePageCB:
    page: int


@dataclass(frozen=True)
class PassCB:
    """No-op callback for layout spacer buttons; dismissed by the stale fallback."""


@dataclass(frozen=True)
class CancelCB:
    """Cancel the defect conversation from any step's inline keyboard."""


@dataclass(frozen=True)
class EditCB:
    """Jump from the summary screen to re-enter a single field."""

    field: str


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


@dataclass(frozen=True)
class LinkConfirmCB:
    """Attach this chat to the employee a deep-link token resolved to."""

    employee_id: int


@dataclass(frozen=True)
class LinkCancelCB:
    """Decline the attachment. The token is already spent either way."""
