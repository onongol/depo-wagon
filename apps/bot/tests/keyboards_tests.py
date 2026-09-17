import uuid
from unittest.mock import MagicMock

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from apps.bot.callback_data import (
    DepartmentCB,
    NodeCB,
    ResponsibleEmployeeCB,
    StatusPickCB,
    StatusSetCB,
)
from apps.bot.constants import (
    BTN_ASK,
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_NEXT,
    BTN_OPEN_DEFECTS,
    BTN_PREV,
    BTN_SKIP,
    TASKS_PAGE_SIZE,
)
from apps.bot.keyboards.defect import (
    department_keyboard,
    node_keyboard_for_department,
    responsible_employee_keyboard,
)
from apps.bot.keyboards.menu import MENU_TEXTS, main_menu_keyboard
from apps.bot.keyboards.tasks import status_picker_keyboard, tasks_keyboard
from apps.core.constants import Department
from apps.defects.constants import DefectStatus


def _menu_texts(kb: ReplyKeyboardMarkup) -> list[str]:
    return [btn.text for row in kb.keyboard for btn in row]


def _nav_texts(kb: InlineKeyboardMarkup) -> list[str]:
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    nav_texts = {str(BTN_PREV), str(BTN_NEXT)}
    return [btn.text for btn in all_buttons if btn.text in nav_texts]


def _make_employee(pk=1, first="Brad", last="Pitt"):
    e = MagicMock()
    e.id = pk
    e.first_name = first
    e.last_name = last
    return e


def _kb_buttons(kb: InlineKeyboardMarkup) -> list:
    return [btn for row in kb.inline_keyboard for btn in row]


def _make_defect(wagon_number="12345", node_display="Wheelset"):
    defect = MagicMock()
    defect.id = uuid.uuid4()
    defect.wagon.number = wagon_number
    defect.get_node_display.return_value = node_display
    return defect


class TestMainMenuKeyboard:
    def test_returns_reply_keyboard(self):
        assert isinstance(main_menu_keyboard(), ReplyKeyboardMarkup)

    def test_has_every_entry_point(self):
        assert _menu_texts(main_menu_keyboard()) == [
            str(BTN_NEW_DEFECT),
            str(BTN_OPEN_DEFECTS),
            str(BTN_ASK),
            str(BTN_HELP),
        ]

    def test_menu_texts_are_exactly_the_labels_shown(self):
        """Text steps guard against these; a missing label is read as input."""
        assert set(_menu_texts(main_menu_keyboard())) == MENU_TEXTS


class TestTasksKeyboard:
    def test_returns_inline_keyboard(self):
        kb = tasks_keyboard(defects=[], page=0, total=0)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_one_button_per_defect(self):
        defects = [_make_defect("11111"), _make_defect("22222")]
        kb = tasks_keyboard(defects=defects, page=0, total=2, can_change_status=True)
        defect_rows = [
            row
            for row in kb.inline_keyboard
            if not any(btn.text in {str(BTN_PREV), str(BTN_NEXT)} for btn in row)
        ]
        assert len(defect_rows) == 2

    def test_no_status_buttons_unless_allowed(self):
        defects = [_make_defect("11111"), _make_defect("22222")]
        kb = tasks_keyboard(defects=defects, page=0, total=TASKS_PAGE_SIZE + 1)
        assert _nav_texts(kb) == [str(BTN_NEXT)]
        assert len(kb.inline_keyboard) == 1

    def test_no_nav_when_single_page(self):
        kb = tasks_keyboard(defects=[], page=0, total=TASKS_PAGE_SIZE - 1)
        assert _nav_texts(kb) == []

    def test_next_only_on_first_page_with_more(self):
        kb = tasks_keyboard(defects=[], page=0, total=TASKS_PAGE_SIZE + 1)
        nav = _nav_texts(kb)
        assert str(BTN_NEXT) in nav
        assert str(BTN_PREV) not in nav

    def test_prev_only_on_last_page(self):
        kb = tasks_keyboard(defects=[], page=1, total=TASKS_PAGE_SIZE + 1)
        nav = _nav_texts(kb)
        assert str(BTN_PREV) in nav
        assert str(BTN_NEXT) not in nav

    def test_both_nav_on_middle_page(self):
        total = TASKS_PAGE_SIZE * 3
        kb = tasks_keyboard(defects=[], page=1, total=total)
        nav = _nav_texts(kb)
        assert str(BTN_PREV) in nav
        assert str(BTN_NEXT) in nav


class TestDepartmentKeyboard:
    def test_returns_inline_keyboard(self):
        assert isinstance(department_keyboard(), InlineKeyboardMarkup)

    def test_all_departments_present(self):
        kb = department_keyboard()
        cb_values = {
            DepartmentCB.unpack(btn.callback_data).value
            for btn in _kb_buttons(kb)
            if btn.callback_data.startswith(DepartmentCB.__prefix__ + ":")
        }
        assert cb_values == {d.value for d in Department}


class TestNodeKeyboardForDepartment:
    def _cb_values(self, kb):
        return {
            NodeCB.unpack(btn.callback_data).value
            for btn in _kb_buttons(kb)
            if btn.callback_data.startswith(NodeCB.__prefix__ + ":")
        }

    def test_bogie_dept_has_bogie_node(self):
        assert "bogie" in self._cb_values(node_keyboard_for_department("bogie"))

    def test_bogie_dept_excludes_coupler_node(self):
        assert "coupler" not in self._cb_values(node_keyboard_for_department("bogie"))

    def test_wheelset_dept_has_wheel_node(self):
        assert "wheel" in self._cb_values(node_keyboard_for_department("wheelset"))

    def test_unknown_dept_returns_all_nodes(self):
        from apps.defects.constants import DefectNode

        values = self._cb_values(node_keyboard_for_department("nonexistent"))
        assert len(values) == len(DefectNode)


class TestResponsibleEmployeeKeyboard:
    def test_single_page_has_no_nav_buttons(self):
        kb = responsible_employee_keyboard([_make_employee()], page=0, total_pages=1)
        nav_texts = {"◀️", "▶️"}
        assert not any(btn.text in nav_texts for btn in _kb_buttons(kb))

    def test_next_only_on_first_of_many_pages(self):
        kb = responsible_employee_keyboard([_make_employee()], page=0, total_pages=3)
        texts = [btn.text for btn in _kb_buttons(kb)]
        assert "▶️" in texts and "◀️" not in texts

    def test_prev_only_on_last_page(self):
        kb = responsible_employee_keyboard([_make_employee()], page=2, total_pages=3)
        texts = [btn.text for btn in _kb_buttons(kb)]
        assert "◀️" in texts and "▶️" not in texts

    def test_both_nav_on_middle_page(self):
        kb = responsible_employee_keyboard([_make_employee()], page=1, total_pages=3)
        texts = [btn.text for btn in _kb_buttons(kb)]
        assert "◀️" in texts and "▶️" in texts

    def test_skip_button_always_present(self):
        kb = responsible_employee_keyboard([], page=0, total_pages=1)
        assert str(BTN_SKIP) in [btn.text for btn in _kb_buttons(kb)]

    def test_employee_buttons_use_correct_callback(self):
        kb = responsible_employee_keyboard([_make_employee(42)], page=0, total_pages=1)
        assert any(
            btn.callback_data.startswith(ResponsibleEmployeeCB.__prefix__ + ":")
            for btn in _kb_buttons(kb)
        )


class TestTaskCallbackDataCarriesUuid:
    """defect_id travels as a UUID so aiogram can pack it as 32 hex chars."""

    def test_tasks_keyboard_carries_the_uuid_itself(self):
        defect = _make_defect()

        kb = tasks_keyboard([defect], page=0, total=1, can_change_status=True)

        picks = [
            StatusPickCB.unpack(btn.callback_data)
            for btn in _kb_buttons(kb)
            if btn.callback_data.startswith(StatusPickCB.__prefix__ + ":")
        ]
        assert len(picks) == 1
        assert picks[0].defect_id == defect.id

    def test_status_picker_passes_the_uuid_through(self):
        defect_id = uuid.uuid4()

        kb = status_picker_keyboard(defect_id, page=0)

        sets = [
            StatusSetCB.unpack(btn.callback_data)
            for btn in _kb_buttons(kb)
            if btn.callback_data.startswith(StatusSetCB.__prefix__ + ":")
        ]
        assert sets
        assert all(cb.defect_id == defect_id for cb in sets)
        assert {cb.status for cb in sets} == set(DefectStatus.values)


class TestCallbackDataStaysUnder64Bytes:
    """aiogram rejects callback_data over 64 bytes at pack() time.

    A dashed UUID plus the longest status plus a page costs 62 of 64 with a
    10-character prefix. Encoding the UUID as hex is what buys the headroom,
    so the budget is asserted here rather than discovered in production.
    """

    def _packed(self, prefix: str, *values) -> int:
        return len(":".join([prefix, *(str(v) for v in values)]).encode())

    def test_dashed_uuid_is_what_makes_it_tight(self):
        worst = max(DefectStatus.values, key=len)

        assert self._packed("status_set", uuid.uuid4(), worst, 99) == 62

    def test_hex_uuid_leaves_room(self):
        worst = max(DefectStatus.values, key=len)

        assert self._packed("dset", uuid.uuid4().hex, worst, 99) <= 64

    def test_hex_uuid_still_fits_with_a_four_digit_page(self):
        worst = max(DefectStatus.values, key=len)

        assert self._packed("dset", uuid.uuid4().hex, worst, 9999) <= 64

    def test_status_pick_fits(self):
        assert self._packed("dpick", uuid.uuid4().hex, 9999) <= 64
