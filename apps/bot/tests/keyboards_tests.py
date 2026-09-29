import uuid
from unittest.mock import MagicMock

from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup

from apps.bot.callback_data import (
    CB_DESC_SKIP,
    CB_MEAS_CLEAR,
    CB_MEAS_DONE,
    CB_STEP_BACK,
    DefectCardCB,
    DepartmentCB,
    EditCB,
    NodeCB,
    ResponsibleEmployeeCB,
    StatusAskCB,
    StatusPickCB,
    StatusSetCB,
    TasksPageCB,
)
from apps.bot.constants import (
    BTN_ALL_EMPLOYEES,
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
    BTN_SAVE,
    BTN_SKIP,
    EDIT_FIELDS,
    EDIT_MEASUREMENTS,
    EDIT_RESPONSIBLE,
    LIST_NUMBER_EMOJI,
    STATUS_TRANSITIONS,
    TASKS_PAGE_SIZE,
)
from apps.bot.keyboards.common import (
    skip_keyboard,
    with_back_button,
)
from apps.bot.keyboards.confirm import confirm_keyboard
from apps.bot.keyboards.defect import department_keyboard, node_keyboard_for_department
from apps.bot.keyboards.measurement import measurement_keyboard
from apps.bot.keyboards.menu import MENU_TEXTS, main_menu_keyboard
from apps.bot.keyboards.responsible_employee import responsible_employee_keyboard
from apps.bot.keyboards.tasks import (
    defect_card_keyboard,
    status_confirm_keyboard,
    status_picker_keyboard,
    tasks_keyboard,
)
from apps.bot.tests.builders import unpacked
from apps.bot.user_data import DefectData
from apps.core.constants import Department
from apps.defects.constants import DefectStatus, DefectType


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

    def test_a_search_can_be_dropped_above_skip(self):
        kb = responsible_employee_keyboard([], page=0, total_pages=1, searching=True)

        assert [[btn.text for btn in row] for row in kb.inline_keyboard[-2:]] == [
            [str(BTN_ALL_EMPLOYEES)],
            [str(BTN_SKIP)],
        ]

    def test_the_whole_list_has_nothing_to_drop(self):
        kb = responsible_employee_keyboard([], page=0, total_pages=1)

        assert str(BTN_ALL_EMPLOYEES) not in [btn.text for btn in _kb_buttons(kb)]

    def test_employee_buttons_use_correct_callback(self):
        kb = responsible_employee_keyboard([_make_employee(42)], page=0, total_pages=1)
        assert any(
            btn.callback_data.startswith(ResponsibleEmployeeCB.__prefix__ + ":")
            for btn in _kb_buttons(kb)
        )


class TestWithBackButton:
    def _rows(self, markup):
        return [[b.callback_data for b in row] for row in markup.inline_keyboard]

    def test_it_goes_first_above_skip(self):
        rows = self._rows(with_back_button(skip_keyboard(CB_DESC_SKIP)))

        assert rows == [[CB_STEP_BACK], [CB_DESC_SKIP]]

    def test_it_goes_under_the_choices_and_above_clear_and_done(self):
        card = measurement_keyboard(any_saved=True, clearable=True)

        rows = self._rows(with_back_button(card))

        assert rows[-3:] == [[CB_STEP_BACK], [CB_MEAS_CLEAR], [CB_MEAS_DONE]]
        assert all(len(row) == 2 for row in rows[:-3])

    def test_under_choices_alone_it_goes_last(self):
        rows = self._rows(with_back_button(department_keyboard()))

        assert rows[-1] == [CB_STEP_BACK]

    def test_a_screen_without_buttons_gets_just_back(self):
        assert self._rows(with_back_button(None)) == [[CB_STEP_BACK]]


class TestConfirmKeyboard:
    def _fields(self, defect):
        return [cb.field for cb in unpacked(confirm_keyboard(defect), EditCB)]

    def test_a_human_factor_offers_the_employee_but_no_measurements(self):
        fields = self._fields(DefectData(defect_type=DefectType.HUMAN_FACTOR))

        assert fields == [k for k, _label in EDIT_FIELDS if k != EDIT_MEASUREMENTS]

    def test_any_other_type_offers_measurements_but_no_employee(self):
        fields = self._fields(DefectData(defect_type=DefectType.WEAR))

        assert fields == [k for k, _label in EDIT_FIELDS if k != EDIT_RESPONSIBLE]

    def test_save_and_cancel_close_it_one_to_a_row(self):
        rows = confirm_keyboard(DefectData()).inline_keyboard

        assert [[b.text for b in row] for row in rows[-2:]] == [
            [str(BTN_SAVE)],
            [str(BTN_CANCEL)],
        ]


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
