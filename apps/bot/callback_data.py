import uuid

from aiogram.filters.callback_data import CallbackData
from pydantic import BaseModel

from apps.defects.constants import DefectStatus

CB_NOOP = "noop"
CB_CANCEL = "cancel"
CB_PART_NUMBER_SKIP = "pn_skip"
CB_RESP_EMP_SKIP = "emp_skip"
CB_RESP_EMP_ALL = "emp_all"
CB_PHOTO_SKIP = "photo_skip"
CB_MEAS_ADD = "meas_add"
CB_MEAS_SKIP = "meas_skip"
CB_MEAS_DONE = "meas_done"
CB_DESC_SKIP = "desc_skip"
CB_DEFECT_CONTINUE = "df_continue"
CB_DEFECT_RESTART = "df_restart"
CB_LINK_CANCEL = "link_cancel"


class DepartmentCB(CallbackData, prefix="dept"):
    value: str


class NodeCB(CallbackData, prefix="node"):
    value: str


class DefectTypeCB(CallbackData, prefix="dtype"):
    value: str


class SeverityCB(CallbackData, prefix="sev"):
    value: str


class DimensionCB(CallbackData, prefix="dim"):
    value: str


class VerdictCB(CallbackData, prefix="vd"):
    value: str


class EditCB(CallbackData, prefix="edit"):
    """Re-open one field from the summary screen."""

    field: str


class ConfirmCB(CallbackData, prefix="cf"):
    confirmed: bool


class ResponsibleEmployeeCB(CallbackData, prefix="emp"):
    employee_id: int


class ResponsibleEmployeePageCB(CallbackData, prefix="emppg"):
    page: int


class TasksPageCB(CallbackData, prefix="tpg"):
    page: int


class LinkConfirmCB(CallbackData, prefix="lnk"):
    """Attach this chat to the employee a deep-link token resolved to."""

    employee_id: int


class DefectRef(BaseModel):
    defect_id: uuid.UUID
    page: int


class StatusRef(BaseModel):
    """52 of Telegram's 64 bytes: no room for another field."""

    defect_id: uuid.UUID
    status: DefectStatus
    page: int


class DefectCardCB(CallbackData, DefectRef, prefix="dcard"): ...


class StatusPickCB(CallbackData, DefectRef, prefix="dpick"): ...


class StatusAskCB(CallbackData, StatusRef, prefix="dask"): ...


class StatusSetCB(CallbackData, StatusRef, prefix="dset"): ...
