"""Inline button payloads.

Replaces the frozen dataclasses in callbacks.py, which relied on PTB's
arbitrary_callback_data — an in-process cache that put a UUID on the wire and
handed the object back. aiogram has no such thing: the payload *is* the string,
which is why buttons here survive a restart and are not worker-local.

Budget. Telegram caps callback_data at 64 bytes and CallbackData.pack() raises
ValueError above it. The cost is len(prefix), then 1 + len(encoded) per field.
A UUID field costs 33 (aiogram encodes it as 32 hex characters, no dashes); an
int costs 1 + its digits; a bool costs 2. A prefix may not contain ":".
StatusSetCB is the tight one at 52 of 64 — it has no room for another string
field. The budget is asserted in callback_data_tests.py rather than trusted.
"""

import uuid

from aiogram.filters.callback_data import CallbackData

from apps.defects.constants import DefectStatus

# Markers carrying nothing. A CallbackData factory for these would only add a
# parse step, so they are plain literals matched with F.data == ...
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
    defect_id: uuid.UUID
    status: DefectStatus
    page: int


LITERALS = frozenset(
    {
        CB_NOOP,
        CB_CANCEL,
        CB_PART_NUMBER_SKIP,
        CB_RESP_EMP_SKIP,
        CB_PHOTO_SKIP,
        CB_MEAS_ADD,
        CB_MEAS_SKIP,
        CB_MEAS_DONE,
        CB_NORM_SKIP,
        CB_UNIT_SKIP,
        CB_DESC_SKIP,
        CB_LINK_CANCEL,
    }
)

FACTORIES = (
    DepartmentCB,
    NodeCB,
    DefectTypeCB,
    SeverityCB,
    DimensionCB,
    VerdictCB,
    EditCB,
    ConfirmCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    TasksPageCB,
    LinkConfirmCB,
    StatusPickCB,
    StatusSetCB,
)
