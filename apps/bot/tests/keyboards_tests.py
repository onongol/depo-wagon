from unittest.mock import MagicMock

import pytest
from telegram import InlineKeyboardMarkup, ReplyKeyboardMarkup

from apps.bot.constants import (
    BTN_HELP,
    BTN_NEW_DEFECT,
    BTN_NEXT,
    BTN_OPEN_DEFECTS,
    BTN_PREV,
    PAGE_SIZE,
)
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.keyboards.tasks import tasks_keyboard
from apps.core.constants import EmployeeRole


def _menu_texts(kb: ReplyKeyboardMarkup) -> list[str]:
    return [btn.text for row in kb.keyboard for btn in row]


def _nav_texts(kb: InlineKeyboardMarkup) -> list[str]:
    all_buttons = [btn for row in kb.inline_keyboard for btn in row]
    nav_texts = {str(BTN_PREV), str(BTN_NEXT)}
    return [btn.text for btn in all_buttons if btn.text in nav_texts]


def _make_defect(wagon_number="12345", node_display="Колесная пара"):
    defect = MagicMock()
    defect.id = "uuid-001"
    defect.wagon.number = wagon_number
    defect.get_node_display.return_value = node_display
    return defect


class TestMainMenuKeyboard:
    def test_returns_reply_keyboard(self):
        kb = main_menu_keyboard(EmployeeRole.INSPECTOR)
        assert isinstance(kb, ReplyKeyboardMarkup)

    @pytest.mark.parametrize("role", list(EmployeeRole))
    def test_all_roles_have_new_defect_button(self, role):
        kb = main_menu_keyboard(role)
        assert str(BTN_NEW_DEFECT) in _menu_texts(kb)

    @pytest.mark.parametrize("role", list(EmployeeRole))
    def test_all_roles_have_help_button(self, role):
        kb = main_menu_keyboard(role)
        assert str(BTN_HELP) in _menu_texts(kb)

    @pytest.mark.parametrize("role", list(EmployeeRole))
    def test_known_roles_have_open_defects_button(self, role):
        kb = main_menu_keyboard(role)
        assert str(BTN_OPEN_DEFECTS) in _menu_texts(kb)

    def test_unknown_role_has_no_open_defects_button(self):
        kb = main_menu_keyboard("unknown_role")
        assert str(BTN_OPEN_DEFECTS) not in _menu_texts(kb)


class TestTasksKeyboard:
    def test_returns_inline_keyboard(self):
        kb = tasks_keyboard(defects=[], page=0, total=0)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_one_button_per_defect(self):
        defects = [_make_defect("11111"), _make_defect("22222")]
        kb = tasks_keyboard(defects=defects, page=0, total=2)
        defect_rows = [
            row
            for row in kb.inline_keyboard
            if not any(btn.text in {str(BTN_PREV), str(BTN_NEXT)} for btn in row)
        ]
        assert len(defect_rows) == 2

    def test_no_nav_when_single_page(self):
        kb = tasks_keyboard(defects=[], page=0, total=PAGE_SIZE - 1)
        assert _nav_texts(kb) == []

    def test_next_only_on_first_page_with_more(self):
        kb = tasks_keyboard(defects=[], page=0, total=PAGE_SIZE + 1)
        nav = _nav_texts(kb)
        assert str(BTN_NEXT) in nav
        assert str(BTN_PREV) not in nav

    def test_prev_only_on_last_page(self):
        kb = tasks_keyboard(defects=[], page=1, total=PAGE_SIZE + 1)
        nav = _nav_texts(kb)
        assert str(BTN_PREV) in nav
        assert str(BTN_NEXT) not in nav

    def test_both_nav_on_middle_page(self):
        total = PAGE_SIZE * 3
        kb = tasks_keyboard(defects=[], page=1, total=total)
        nav = _nav_texts(kb)
        assert str(BTN_PREV) in nav
        assert str(BTN_NEXT) in nav
