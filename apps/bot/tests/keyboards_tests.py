import uuid
from unittest.mock import MagicMock

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from apps.bot.callback_data import (
    DefectCardCB,
    DepartmentCB,
    NodeCB,
    ResponsibleEmployeeCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
)
from apps.bot.constants import (
    BTN_ASK,
    BTN_BACK,
    BTN_CANCEL,
    BTN_CHANGE_STATUS,
    BTN_CONFIRM,
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_NEXT,
    BTN_OPEN_DEFECTS,
    BTN_PAGE_NEXT,
    BTN_PAGE_PREV,
    BTN_PREV,
    BTN_SKIP,
    LIST_NUMBER_EMOJI,
    STATUS_TRANSITIONS,
    TASKS_PAGE_SIZE,
)
from apps.bot.keyboards.defect import department_keyboard, node_keyboard_for_department
from apps.bot.keyboards.menu import MENU_TEXTS, main_menu_keyboard
from apps.bot.keyboards.responsible_employee import responsible_employee_keyboard
from apps.bot.keyboards.tasks import (
    defect_card_keyboard,
    status_confirm_keyboard,
    status_picker_keyboard,
    tasks_keyboard,
)
from apps.bot.tests.builders import unpacked
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
    defect.severity = "high"
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
        kb = tasks_keyboard(defects=[], page=0, pages=1)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_the_defects_share_one_row_of_numbers(self):
        defects = [_make_defect() for _ in range(TASKS_PAGE_SIZE)]
        kb = tasks_keyboard(defects=defects, page=0, pages=2)

        assert [btn.text for btn in kb.inline_keyboard[0]] == list(
            LIST_NUMBER_EMOJI[:TASKS_PAGE_SIZE]
        )

    def test_every_defect_button_opens_its_card_on_this_page(self):
        defects = [_make_defect("11111"), _make_defect("22222")]
        kb = tasks_keyboard(defects=defects, page=3, pages=5)

        cards = unpacked(kb, DefectCardCB)

        assert [cb.defect_id for cb in cards] == [d.id for d in defects]
        assert {cb.page for cb in cards} == {3}

    def test_the_list_itself_changes_no_status(self):
        kb = tasks_keyboard(defects=[_make_defect()], page=0, pages=1)

        assert unpacked(kb, StatusPickCB) == []
        assert unpacked(kb, StatusSetCB) == []

    def test_a_page_never_runs_out_of_numbers(self):
        assert len(LIST_NUMBER_EMOJI) >= TASKS_PAGE_SIZE

    def test_no_nav_when_single_page(self):
        kb = tasks_keyboard(defects=[], page=0, pages=1)
        assert _nav_texts(kb) == []

    def test_next_only_on_first_page_with_more(self):
        kb = tasks_keyboard(defects=[], page=0, pages=2)
        nav = _nav_texts(kb)
        assert str(BTN_NEXT) in nav
        assert str(BTN_PREV) not in nav

    def test_prev_only_on_last_page(self):
        kb = tasks_keyboard(defects=[], page=1, pages=2)
        nav = _nav_texts(kb)
        assert str(BTN_PREV) in nav
        assert str(BTN_NEXT) not in nav

    def test_both_nav_on_middle_page(self):
        kb = tasks_keyboard(defects=[], page=1, pages=3)
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
        nav_texts = {BTN_PAGE_PREV, BTN_PAGE_NEXT}
        assert not any(btn.text in nav_texts for btn in _kb_buttons(kb))

    def test_next_only_on_first_of_many_pages(self):
        kb = responsible_employee_keyboard([_make_employee()], page=0, total_pages=3)
        texts = [btn.text for btn in _kb_buttons(kb)]
        assert BTN_PAGE_NEXT in texts and BTN_PAGE_PREV not in texts

    def test_prev_only_on_last_page(self):
        kb = responsible_employee_keyboard([_make_employee()], page=2, total_pages=3)
        texts = [btn.text for btn in _kb_buttons(kb)]
        assert BTN_PAGE_PREV in texts and BTN_PAGE_NEXT not in texts

    def test_both_nav_on_middle_page(self):
        kb = responsible_employee_keyboard([_make_employee()], page=1, total_pages=3)
        texts = [btn.text for btn in _kb_buttons(kb)]
        assert BTN_PAGE_PREV in texts and BTN_PAGE_NEXT in texts

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

        kb = tasks_keyboard([defect], page=0, pages=1)

        [card] = unpacked(kb, DefectCardCB)
        assert card.defect_id == defect.id

    def test_status_picker_passes_the_uuid_through(self):
        defect_id = uuid.uuid4()
        targets = STATUS_TRANSITIONS[DefectStatus.OPEN]

        kb = status_picker_keyboard(defect_id, targets, page=0)

        asks = unpacked(kb, StatusAskCB)
        assert asks
        assert all(cb.defect_id == defect_id for cb in asks)


class TestDefectCardKeyboard:
    def test_offers_the_status_change_when_allowed(self):
        defect_id = uuid.uuid4()

        kb = defect_card_keyboard(defect_id, page=2, can_change=True)

        [pick] = unpacked(kb, StatusPickCB)
        assert (pick.defect_id, pick.page) == (defect_id, 2)
        assert str(BTN_CHANGE_STATUS) in [b.text for b in _kb_buttons(kb)]

    def test_hides_the_status_change_otherwise(self):
        kb = defect_card_keyboard(uuid.uuid4(), page=0, can_change=False)

        assert unpacked(kb, StatusPickCB) == []

    def test_returns_to_the_same_page_of_the_list(self):
        kb = defect_card_keyboard(uuid.uuid4(), page=4, can_change=False)

        [back] = unpacked(kb, TasksPageCB)
        assert back.page == 4
        assert _kb_buttons(kb)[-1].text == str(BTN_BACK)


class TestStatusPickerKeyboard:
    def test_offers_only_the_given_statuses(self):
        targets = (DefectStatus.OPEN, DefectStatus.CLOSED)

        kb = status_picker_keyboard(uuid.uuid4(), targets, page=0)

        assert [cb.status for cb in unpacked(kb, StatusAskCB)] == list(targets)

    def test_picking_asks_first_rather_than_saving(self):
        kb = status_picker_keyboard(uuid.uuid4(), (DefectStatus.CLOSED,), page=0)

        assert unpacked(kb, StatusSetCB) == []

    def test_back_returns_to_the_card(self):
        defect_id = uuid.uuid4()

        kb = status_picker_keyboard(defect_id, (DefectStatus.CLOSED,), page=3)

        [card] = unpacked(kb, DefectCardCB)
        assert (card.defect_id, card.page) == (defect_id, 3)
        assert _kb_buttons(kb)[-1].text == str(BTN_BACK)


class TestStatusConfirmKeyboard:
    def test_confirm_saves_the_picked_status(self):
        defect_id = uuid.uuid4()

        kb = status_confirm_keyboard(defect_id, DefectStatus.CLOSED, page=1)

        [save] = unpacked(kb, StatusSetCB)
        assert (save.defect_id, save.status, save.page) == (
            defect_id,
            DefectStatus.CLOSED,
            1,
        )

    def test_cancel_returns_to_the_card(self):
        defect_id = uuid.uuid4()

        kb = status_confirm_keyboard(defect_id, DefectStatus.CLOSED, page=1)

        [card] = unpacked(kb, DefectCardCB)
        assert card.defect_id == defect_id
        assert [b.text for b in _kb_buttons(kb)] == [str(BTN_CONFIRM), str(BTN_CANCEL)]


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
