"""Tests for the aiogram callback payloads.

The budget test is the valuable one: it turns the 64-byte limit from a comment
into a property of the build, so adding a field to a factory fails here rather
than at runtime inside keyboard construction.
"""

import uuid

import pytest
from aiogram.filters.callback_data import CallbackData

from apps.bot.callback_data import (
    FACTORIES,
    LITERALS,
    ConfirmCB,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    LinkConfirmCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    SeverityCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
    VerdictCB,
    is_known_callback,
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

    def test_status_pick_with_a_four_digit_page(self):
        cb = StatusPickCB(defect_id=uuid.uuid4(), page=9999)

        assert _size(cb) <= TELEGRAM_LIMIT

    def test_ids_and_pages_at_implausible_magnitudes(self):
        assert _size(ResponsibleEmployeeCB(employee_id=9999999999)) <= TELEGRAM_LIMIT
        assert _size(LinkConfirmCB(employee_id=9999999999)) <= TELEGRAM_LIMIT
        assert _size(ResponsibleEmployeePageCB(page=9999)) <= TELEGRAM_LIMIT
        assert _size(TasksPageCB(page=9999)) <= TELEGRAM_LIMIT

    def test_every_literal_fits(self):
        assert all(len(v.encode()) <= TELEGRAM_LIMIT for v in LITERALS)

    def test_the_tightest_payload_still_has_headroom(self):
        """StatusSetCB is the one with no room for another string field."""
        worst = max(DefectStatus.values, key=len)
        cb = StatusSetCB(defect_id=uuid.uuid4(), status=worst, page=99)

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
    def test_prefixes_are_unique(self):
        prefixes = [f.__prefix__ for f in FACTORIES]

        assert len(prefixes) == len(set(prefixes))

    def test_no_prefix_contains_the_separator(self):
        assert all(":" not in f.__prefix__ for f in FACTORIES)

    def test_literals_do_not_collide_with_any_prefix(self):
        prefixes = {f.__prefix__ for f in FACTORIES}

        assert not (LITERALS & prefixes)


class TestIsKnownCallback:
    @pytest.mark.parametrize("literal", sorted(LITERALS))
    def test_recognises_every_literal(self, literal):
        assert is_known_callback(literal)

    def test_recognises_a_packed_factory_payload(self):
        assert is_known_callback(DepartmentCB(value="bogie").pack())
        assert is_known_callback(
            StatusSetCB(defect_id=uuid.uuid4(), status="open", page=0).pack()
        )

    def test_rejects_a_pre_migration_ptb_payload(self):
        """PTB put a bare UUID on the wire; those must reach the loud handler."""
        assert not is_known_callback(uuid.uuid4().hex)

    def test_rejects_an_empty_payload(self):
        assert not is_known_callback("")

    def test_rejects_a_known_prefix_with_the_wrong_field_count(self):
        """Schema drift after a deploy — must not be silently swallowed."""
        assert not is_known_callback("dset:" + uuid.uuid4().hex)
        assert not is_known_callback("emppg:1:2:3")

    def test_rejects_a_known_prefix_with_an_unparsable_field(self):
        assert not is_known_callback("tpg:not_a_number")
        assert not is_known_callback(f"dpick:{'z' * 32}:0")

    def test_rejects_an_unknown_prefix(self):
        assert not is_known_callback("nope:1")
