"""Inline button payloads. The payload *is* the string on the wire, so a button
survives a restart and is not worker-local.

Prefixes must be unique: aiogram does not check, and a duplicate silently sends
both classes' buttons to whichever router was included first. Asserted in
callback_data_tests.py rather than trusted.
"""

import uuid

from aiogram.filters.callback_data import CallbackData

from apps.defects.constants import DefectStatus

CB_NOOP = "noop"
CB_CANCEL = "cancel"
CB_PART_NUMBER_SKIP = "pn_skip"
CB_RESP_EMP_SKIP = "emp_skip"
CB_PHOTO_SKIP = "photo_skip"
CB_MEAS_ADD = "meas_add"
CB_MEAS_SKIP = "meas_skip"
CB_MEAS_DONE = "meas_done"
CB_NORM_SKIP = "norm_skip"
CB_UNIT_SKIP = "unit_skip"
CB_DESC_SKIP = "desc_skip"
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


class StatusPickCB(CallbackData, prefix="dpick"):
    defect_id: uuid.UUID
    page: int


class StatusSetCB(CallbackData, prefix="dset"):
    """The tight one: 52 of Telegram's 64 bytes, no room for another field.

    Cost is len(prefix), then 1 + len(encoded) per field — UUID 33 (32 hex, no
    dashes), int 1 + digits, bool 2. pack() raises above 64.
    """

    defect_id: uuid.UUID
    status: DefectStatus
    page: int
