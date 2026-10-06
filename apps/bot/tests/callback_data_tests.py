"""Tests for the aiogram callback payloads.

The budget test is the valuable one: it turns the 64-byte limit from a comment
into a property of the build, so adding a field to a factory fails here rather
than at runtime inside keyboard construction.
"""

import uuid

import pytest
from aiogram.filters.callback_data import CallbackData

from apps.bot import callback_data
from apps.bot.callback_data import (
    ConfirmCB,
    DefectCardCB,
    DefectOpenCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    LinkConfirmCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    SeverityCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
    VerdictCB,
)
from apps.bot.constants import EDIT_FIELDS
from apps.core.constants import Department
from apps.defects.constants import (
    DefectNode,
    DefectSeverity,
    DefectStatus,
    DefectType,
    DefectVerdict,
    MeasurementDimension,
)

TELEGRAM_LIMIT = 64


def _factories() -> list[type[CallbackData]]:
    """Every payload class in the module, read off it rather than listed here.

    Deliberately not exported from callback_data itself: routing has no use for
    such a list, and one kept in the module would be a second thing to maintain
    when a factory is added. Read at call time so a new class is covered on
    sight, and the emptiness guard below is what stops that being vacuous.
    """
    return [
        obj
        for obj in vars(callback_data).values()
        if isinstance(obj, type)
        and issubclass(obj, CallbackData)
        and obj is not CallbackData
    ]


def _size(cb) -> int:
    return len(cb.pack().encode())


class TestBudget:
    """Every payload the bot can actually build must fit in 64 bytes."""

    @pytest.mark.parametrize("value", Department.values)
    def test_department(self, value):
        assert _size(DepartmentCB(value=value)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("value", DefectNode.values)
    def test_node(self, value):
        assert _size(NodeCB(value=value)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("value", DefectType.values)
    def test_defect_type(self, value):
        assert _size(DefectTypeCB(value=value)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("value", DefectVerdict.values)
    def test_verdict(self, value):
        assert _size(VerdictCB(value=value)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("value", DefectSeverity.values)
    def test_severity(self, value):
        assert _size(SeverityCB(value=value)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("value", MeasurementDimension.values)
    def test_dimension(self, value):
        assert _size(DimensionCB(value=value)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("field", [key for key, _label in EDIT_FIELDS])
    def test_edit(self, field):
        assert _size(EditCB(field=field)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("status", DefectStatus.values)
    def test_status_set_with_a_four_digit_page(self, status):
        cb = StatusSetCB(defect_id=uuid.uuid4(), status=status, page=9999)

        assert _size(cb) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("status", DefectStatus.values)
    def test_status_ask_with_a_four_digit_page(self, status):
        cb = StatusAskCB(defect_id=uuid.uuid4(), status=status, page=9999)

        assert _size(cb) <= TELEGRAM_LIMIT

    def test_status_pick_with_a_four_digit_page(self):
        cb = StatusPickCB(defect_id=uuid.uuid4(), page=9999)

        assert _size(cb) <= TELEGRAM_LIMIT

    def test_defect_card_with_a_four_digit_page(self):
        cb = DefectCardCB(defect_id=uuid.uuid4(), page=9999)

        assert _size(cb) <= TELEGRAM_LIMIT

    def test_defect_open(self):
        assert _size(DefectOpenCB(defect_id=uuid.uuid4())) <= TELEGRAM_LIMIT

    def test_ids_and_pages_at_implausible_magnitudes(self):
        assert _size(ResponsibleEmployeeCB(employee_id=9999999999)) <= TELEGRAM_LIMIT
        assert _size(LinkConfirmCB(employee_id=9999999999)) <= TELEGRAM_LIMIT
        assert _size(ResponsibleEmployeePageCB(page=9999)) <= TELEGRAM_LIMIT
        assert _size(TasksPageCB(page=9999)) <= TELEGRAM_LIMIT

    @pytest.mark.parametrize("factory", [StatusSetCB, StatusAskCB])
    def test_the_tightest_payloads_still_have_headroom(self, factory):
        """No room for another string field, such as the status being left."""
        worst = max(DefectStatus.values, key=len)
        cb = factory(defect_id=uuid.uuid4(), status=worst, page=99)

        assert _size(cb) == 52


class TestEncoding:
    def test_uuid_travels_as_hex_without_dashes(self):
        defect_id = uuid.uuid4()

        packed = StatusPickCB(defect_id=defect_id, page=0).pack()

        assert defect_id.hex in packed
        assert str(defect_id) not in packed

    def test_uuid_round_trips_to_a_uuid(self):
        defect_id = uuid.uuid4()

        restored = StatusPickCB.unpack(StatusPickCB(defect_id=defect_id, page=3).pack())

        assert restored.defect_id == defect_id
        assert restored.page == 3

    def test_bool_round_trips(self):
        assert ConfirmCB.unpack(ConfirmCB(confirmed=True).pack()).confirmed is True
        assert ConfirmCB.unpack(ConfirmCB(confirmed=False).pack()).confirmed is False

    def test_status_round_trips_to_the_enum(self):
        cb = StatusSetCB(
            defect_id=uuid.uuid4(), status=DefectStatus.IN_PROGRESS, page=0
        )

        restored = StatusSetCB.unpack(cb.pack())

        assert restored.status == DefectStatus.IN_PROGRESS

    def test_an_oversize_payload_raises_rather_than_truncating(self):
        class Oversize(CallbackData, prefix="x" * 40):
            defect_id: uuid.UUID
            status: str
            page: int

        with pytest.raises(ValueError, match="too long"):
            Oversize(defect_id=uuid.uuid4(), status="in_progress", page=9999).pack()


class TestPrefixes:
    """The one collision nothing else catches.

    aiogram rejects a prefix containing the separator at class definition, so
    that needs no test — the module would not import. A duplicate prefix it
    accepts happily, and the failure is silent: both classes' filters match the
    same payload, the earlier-included router wins, and the loser's buttons go
    to the wrong handler with a correctly-typed object.
    """

    def test_prefixes_are_unique(self):
        prefixes = [f.__prefix__ for f in _factories()]

        assert len(prefixes) == len(set(prefixes))

    def test_the_module_is_actually_being_read(self):
        """Without this, a rename would make the check above pass on nothing."""
        factories = _factories()

        assert len(factories) > 10
        assert StatusSetCB in factories


class TestDriftedPayloadsStopMatching:
    """The assumption the whole fallback rests on, pinned at the definitions.

    Routing no longer asks whether a payload is known — it lets every factory's
    own filter decline and treats the leftovers as dead. That only separates a
    live button from a stale one because unpack is strict about arity and field
    types, so these are the cases a deploy actually produces.
    """

    @pytest.mark.parametrize(
        ("factory", "data"),
        [
            (StatusSetCB, "dset:" + uuid.uuid4().hex),
            (ResponsibleEmployeePageCB, "emppg:1:2:3"),
            (TasksPageCB, "tpg:not_a_number"),
            (StatusPickCB, f"dpick:{'z' * 32}:0"),
            (StatusAskCB, f"dask:{uuid.uuid4().hex}:reopened:0"),
            (DefectCardCB, "dcard:" + uuid.uuid4().hex),
        ],
    )
    def test_a_shape_change_fails_to_unpack(self, factory, data):
        with pytest.raises((TypeError, ValueError)):
            factory.unpack(data)

    def test_a_current_payload_still_unpacks(self):
        packed = StatusSetCB(defect_id=uuid.uuid4(), status="open", page=0).pack()

        assert StatusSetCB.unpack(packed).page == 0
