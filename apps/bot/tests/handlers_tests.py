"""Tests for the defect registration steps and the shared utility handlers.

Every step now round-trips its form through storage, so a loaded DefectData is
a detached copy — the assertions read it back rather than holding a reference.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.utils.text_decorations import html_decoration

from apps.bot.callback_data import (
    CB_CANCEL,
    CB_DESC_SKIP,
    CB_PHOTO_CLEAR,
    CB_PHOTO_SKIP,
    CB_RESP_EMP_SKIP,
    CB_STEP_BACK,
    DefectTypeCB,
    DepartmentCB,
    DimensionCB,
    EditCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    SeverityCB,
    VerdictCB,
)
from apps.bot.constants import (
    BTN_ASK,
    BTN_CANCEL,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
    BTN_SAVE,
    EDIT_MEASUREMENTS,
    EDIT_RESPONSIBLE,
    UD_DEFECT,
    UD_EDITING,
    UD_RESP_SEARCH,
    UD_SCREEN,
)
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.common.cancel import cancel
from apps.bot.handlers.common.help import help_command
from apps.bot.handlers.common.text import build_cancelled_text, build_help_text
from apps.bot.handlers.defect.defect_type import DefectTypeScene
from apps.bot.handlers.defect.department import DepartmentScene
from apps.bot.handlers.defect.description import DescriptionScene
from apps.bot.handlers.defect.measurement import MeasurementChoiceScene
from apps.bot.handlers.defect.node import NodeScene
from apps.bot.handlers.defect.part_number import (
    PART_NUMBER_MAX_LENGTH,
    PartNumberScene,
)
from apps.bot.handlers.defect.photo import PhotoScene
from apps.bot.handlers.defect.responsible_employee import ResponsibleEmployeeScene
from apps.bot.handlers.defect.responsible_employee.list import EMPLOYEE_PAGE_SIZE
from apps.bot.handlers.defect.severity import SeverityScene
from apps.bot.handlers.defect.start import new_defect_start
from apps.bot.handlers.defect.summary import SummaryScene
from apps.bot.handlers.defect.text import (
    build_ask_defect_type_text,
    build_ask_department_text,
    build_ask_description_text,
    build_ask_measurement_text,
    build_ask_more_photos_text,
    build_ask_photo_text,
    build_ask_responsible_employee_text,
    build_ask_severity_text,
    build_ask_value_text,
    build_ask_verdict_text,
    build_description_too_long_text,
    build_edit_description_text,
    build_edit_node_text,
    build_edit_photos_text,
    build_edit_severity_text,
    build_edit_verdict_text,
    build_editing_heading,
    build_responsible_employee_search_text,
    build_review_heading,
    build_save_question_text,
    build_step_heading,
    build_value_invalid_text,
    build_wagon_not_found_text,
)
from apps.bot.handlers.defect.verdict import VerdictScene
from apps.bot.handlers.defect.wagon import WagonScene
from apps.bot.keyboards.common import (
    clear_or_done_keyboard,
    done_keyboard,
    skip_keyboard,
    with_step_buttons,
)
from apps.bot.keyboards.confirm import confirm_keyboard, employee_verdict_keyboard
from apps.bot.keyboards.defect import (
    defect_type_keyboard,
    department_keyboard,
    severity_keyboard,
)
from apps.bot.keyboards.measurement import (
    measurement_keyboard,
    measurement_value_keyboard,
)
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.tests.builders import (
    CHAT_ID,
    SENT_ID,
    make_callback,
    make_message,
)
from apps.bot.user_data import DefectData, MeasurementEntry, PhotoEntry
from apps.bot.utils.unregistered import build_not_registered_text
from apps.defects.constants import DefectNode, DefectType, DefectVerdict

WAGON_LOOKUP = "apps.bot.handlers.defect.wagon.services.get_wagon_by_number"


def _make_employee(pk=1, first="Bat", last="Erdene"):
    return MagicMock(id=pk, first_name=first, last_name=last)


@pytest.fixture
def picker():
    """The picker's three queries, answered without a database."""
    with (
        patch(
            "apps.bot.services.count_department_employees", AsyncMock(return_value=0)
        ) as count,
        patch(
            "apps.bot.services.get_department_employees", AsyncMock(return_value=[])
        ) as page,
        patch(
            "apps.bot.services.get_department_employee", AsyncMock(return_value=None)
        ) as one,
    ):
        yield MagicMock(count=count, page=page, one=one)


class TestCancelHandler:
    async def test_clears_everything_the_conversation_stored(self, state):
        await state.set_state(DefectSG.node)
        await state.update_data({UD_DEFECT: {"node": "wheel"}})

        await cancel(make_message(), state)

        assert await state.get_data() == {}
        assert await state.get_state() is None

    async def test_replies_with_the_menu_the_defect_form_hid(self, state):
        message = make_message()

        await cancel(message, state)

        message.answer.assert_awaited_once_with(
            **build_cancelled_text().as_kwargs(), reply_markup=main_menu_keyboard()
        )

    async def test_tolerates_an_idle_conversation(self, state):
        await cancel(make_message(), state)

        assert await state.get_state() is None


class TestHelpHandler:
    async def test_replies_with_help_text(self):
        message = make_message()

        await help_command(message)

        message.answer.assert_awaited_once_with(**build_help_text().as_kwargs())

    def test_names_the_buttons_as_the_keyboard_shows_them(self):
        text = build_help_text().render()[0]
        buttons = (BTN_NEW_DEFECT, BTN_SAVE, BTN_OPEN_DEFECTS, BTN_ASK, BTN_CANCEL)
        for button in buttons:
            assert str(button) in text


class TestNewDefectStart:
    async def test_opens_a_blank_form_in_the_wagon_scene(self, state):
        """The screen is the scene's to draw; see the flow tests for it."""
        scenes = AsyncMock()

        await new_defect_start(make_message(), state, MagicMock(), scenes)

        scenes.enter.assert_awaited_once_with(DefectSG.wagon_num)
        assert await load_defect(state) == DefectData()

    async def test_drops_what_an_abandoned_form_left_behind(self, state):
        """Edit, then /ask, then New Defect: the entry runs outside DefectSG."""
        await state.update_data({UD_EDITING: True, UD_RESP_SEARCH: "bat"})

        await new_defect_start(make_message(), state, MagicMock(), AsyncMock())

        data = await state.get_data()
        assert UD_EDITING not in data
        assert UD_RESP_SEARCH not in data


class TestReceiveWagonNumber:
    async def test_an_unknown_number_is_named_on_the_screen(self, state):
        """An entity, not HTML: markup in what the user typed needs no escaping."""
        await save_defect(state, DefectData())
        message = make_message("<b>80035668</b>")

        with patch(WAGON_LOOKUP, AsyncMock(return_value=None)):
            await WagonScene(wizard=MagicMock()).receive(message, state)

        message.delete.assert_awaited_once()
        notice = build_wagon_not_found_text("<b>80035668</b>")
        content, _ = await WagonScene.draw(DefectData(), {}, notice=notice)
        sent = message.bot.send_message.await_args.kwargs
        assert (sent["text"], sent["entities"]) == content.render()
        assert await state.get_state() is None

    async def test_a_known_number_goes_on_to_the_department_scene(self, state):
        """Its screen is the department scene's to draw; see the flow tests."""
        await save_defect(state, DefectData())
        scene = WagonScene(wizard=AsyncMock())
        wagon = MagicMock(id=3, number="80035668")

        with patch(WAGON_LOOKUP, AsyncMock(return_value=wagon)):
            await scene.receive(make_message("80035668"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.department)
        assert (await load_defect(state)).wagon_id == 3


class TestReceiveDepartment:
    async def test_saves_department_and_its_label(self, state):
        await save_defect(state, DefectData())

        await DepartmentScene(wizard=AsyncMock()).receive(
            make_callback(), DepartmentCB(value="bogie"), state
        )

        defect = await load_defect(state)
        assert defect.department == "bogie"
        assert defect.department_label

    async def test_goes_on_to_the_node_scene(self, state):
        """Its screen is the node scene's to draw; see the flow tests."""
        await save_defect(state, DefectData())
        scene = DepartmentScene(wizard=AsyncMock())

        await scene.receive(make_callback(), DepartmentCB(value="bogie"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.node)


class TestReceiveNode:
    async def test_saves_node_and_its_label(self, state):
        await save_defect(state, DefectData())

        await NodeScene(wizard=AsyncMock()).receive(
            make_callback(), NodeCB(value="wheel"), state
        )

        defect = await load_defect(state)
        assert defect.node == "wheel"
        assert defect.node_label

    async def test_goes_on_to_the_part_number_scene(self, state):
        await save_defect(state, DefectData())
        scene = NodeScene(wizard=AsyncMock())

        await scene.receive(make_callback(), NodeCB(value=DefectNode.WHEEL), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.part_number)

    async def test_an_edit_goes_back_to_the_summary(self, state):
        await save_defect(state, DefectData(department="bogie"))
        await state.update_data({UD_EDITING: True})
        scene = NodeScene(wizard=AsyncMock())

        await scene.receive(make_callback(), NodeCB(value="wheel"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)


class TestReceivePartNumber:
    """Its screen after is the defect type scene's; see the flow tests."""

    async def test_text_input_saves_the_part_number(self, state):
        await save_defect(state, DefectData())

        await PartNumberScene(wizard=AsyncMock()).receive(
            make_message("ABC-1234"), state
        )

        assert (await load_defect(state)).part_number == "ABC-1234"

    async def test_text_input_goes_on_to_the_defect_type_scene(self, state):
        await save_defect(state, DefectData())
        scene = PartNumberScene(wizard=AsyncMock())

        await scene.receive(make_message("P-001"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.defect_type)

    async def test_a_part_number_at_the_column_limit_is_saved(self, state):
        await save_defect(state, DefectData())
        scene = PartNumberScene(wizard=AsyncMock())

        await scene.receive(make_message("x" * PART_NUMBER_MAX_LENGTH), state)

        assert (await load_defect(state)).part_number == "x" * PART_NUMBER_MAX_LENGTH
        scene.wizard.goto.assert_awaited_once()

    async def test_a_longer_part_number_stays_and_the_screen_goes_under_it(self, state):
        """Left in the chat, to be copied and shortened."""
        await save_defect(state, DefectData())
        scene = PartNumberScene(wizard=AsyncMock())
        message = make_message("x" * (PART_NUMBER_MAX_LENGTH + 1))

        await scene.receive(message, state)

        assert (await load_defect(state)).part_number == ""
        scene.wizard.goto.assert_not_awaited()
        message.delete.assert_not_awaited()
        screen = message.bot.send_message.await_args.kwargs["text"]
        assert f"{PART_NUMBER_MAX_LENGTH + 1}/{PART_NUMBER_MAX_LENGTH}" in screen

    async def test_skip_clears_the_part_number(self, state):
        await save_defect(state, DefectData(part_number="old"))

        await PartNumberScene(wizard=AsyncMock()).skip(make_callback(), state)

        assert (await load_defect(state)).part_number == ""

    async def test_skip_goes_on_to_the_defect_type_scene(self, state):
        await save_defect(state, DefectData())
        scene = PartNumberScene(wizard=AsyncMock())

        await scene.skip(make_callback(), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.defect_type)

    async def test_skip_after_an_edit_goes_back_to_the_summary(self, state):
        """After=After.goto(...) could not: its destination would be fixed."""
        await save_defect(state, DefectData(part_number="old"))
        await state.update_data({UD_EDITING: True})
        scene = PartNumberScene(wizard=AsyncMock())

        await scene.skip(make_callback(), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)
        assert (await load_defect(state)).part_number == ""


class TestReceiveDefectType:
    async def test_saves_the_type(self, state):
        await save_defect(state, DefectData())

        await DefectTypeScene(wizard=AsyncMock()).receive(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        assert (await load_defect(state)).defect_type == DefectType.HUMAN_FACTOR

    async def test_every_other_type_goes_on_to_the_photo_scene(self, state):
        """Its screen is the photo scene's to draw; see TestPhotoSceneScreen."""
        for value in set(DefectType.values) - {DefectType.HUMAN_FACTOR}:
            await save_defect(state, DefectData())
            scene = DefectTypeScene(wizard=AsyncMock())

            await scene.receive(make_callback(), DefectTypeCB(value=value), state)

            scene.wizard.goto.assert_awaited_once_with(DefectSG.photo)

    async def test_a_human_factor_goes_on_to_the_employee_scene(self, state):
        await save_defect(state, DefectData())
        scene = DefectTypeScene(wizard=AsyncMock())

        await scene.receive(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        scene.wizard.goto.assert_awaited_once_with(DefectSG.responsible_employee)

    async def test_a_human_factor_asks_for_the_employee_after_an_edit_too(self, state):
        """The employee scene goes back to the summary itself."""
        await save_defect(state, DefectData(defect_type=DefectType.WEAR))
        await state.update_data({UD_EDITING: True})
        scene = DefectTypeScene(wizard=AsyncMock())

        await scene.receive(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        scene.wizard.goto.assert_awaited_once_with(DefectSG.responsible_employee)
        assert (await state.get_data())[UD_EDITING] is True

    async def test_a_human_factor_again_keeps_the_employee_it_has(self, state):
        """Its list would offer only Skip or another pick: either loses this one."""
        await save_defect(
            state,
            DefectData(
                defect_type=DefectType.HUMAN_FACTOR,
                responsible_employee_id=5,
                responsible_employee_label="X Y",
            ),
        )
        await state.update_data({UD_EDITING: True})
        scene = DefectTypeScene(wizard=AsyncMock())

        await scene.receive(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)
        assert (await load_defect(state)).responsible_employee_id == 5

    async def test_another_type_drops_the_employee(self, state):
        """Edit ▸ Type away from a human factor must not save its employee."""
        await save_defect(
            state,
            DefectData(
                defect_type=DefectType.HUMAN_FACTOR,
                responsible_employee_id=5,
                responsible_employee_label="X Y",
            ),
        )

        await DefectTypeScene(wizard=AsyncMock()).receive(
            make_callback(), DefectTypeCB(value=DefectType.WEAR), state
        )

        defect = await load_defect(state)
        assert defect.responsible_employee_id is None
        assert defect.responsible_employee_label is None

    async def test_the_screen_asks_for_the_type(self):
        text, keyboard = await DefectTypeScene.screen(DefectData(), {})

        assert text.render() == build_ask_defect_type_text().render()
        assert keyboard == defect_type_keyboard()

    async def test_the_part_number_is_shown_as_typed(self, state):
        """An entity, not HTML: markup in what the user typed needs no escaping."""
        await save_defect(state, DefectData())

        await PartNumberScene(wizard=AsyncMock()).receive(make_message("<A&B>"), state)
        form = await load_defect(state)
        text, _ = await DefectTypeScene.draw(form, {})

        assert form.part_number == "<A&B>"
        assert "🔢 Part number: <A&B>" in text.render()[0]


class TestPhotoSceneScreen:
    async def test_before_any_it_asks_for_one_with_skip(self):
        text, keyboard = await PhotoScene.screen(DefectData(), {})

        assert text.render() == build_ask_photo_text().render()
        assert keyboard == skip_keyboard(CB_PHOTO_SKIP)

    async def test_after_one_it_asks_for_more_with_done(self):
        form = DefectData(photos=[PhotoEntry(file_id="a", message_id=1)])

        text, keyboard = await PhotoScene.screen(form, {})

        assert text.render() == build_ask_more_photos_text().render()
        assert keyboard == done_keyboard(CB_PHOTO_SKIP)

    async def test_after_a_human_factor_the_fields_name_the_employee(self):
        form = DefectData(
            defect_type=DefectType.HUMAN_FACTOR, responsible_employee_label="Bold Bat"
        )

        text, _ = await PhotoScene.draw(form, {})

        assert "👤 Responsible: Bold Bat" in text.render()[0]

    async def test_after_a_human_factor_a_skipped_employee_is_a_dash(self):
        form = DefectData(defect_type=DefectType.HUMAN_FACTOR)

        text, _ = await PhotoScene.draw(form, {})

        assert "👤 Responsible: —" in text.render()[0]


class TestSeverityScene:
    async def test_the_screen_asks_for_it(self):
        text, keyboard = await SeverityScene.screen(DefectData(), {})

        assert text.render() == build_ask_severity_text().render()
        assert keyboard == severity_keyboard()

    async def test_a_skipped_description_is_a_dash_above_it(self):
        text, _ = await SeverityScene.draw(DefectData(), {})

        assert "📝 Description: —" in text.render()[0]

    async def test_an_edit_asks_for_it_again(self):
        text, keyboard = await SeverityScene.screen(DefectData(), {UD_EDITING: True})

        assert text.render() == build_edit_severity_text().render()
        assert keyboard == severity_keyboard()

    async def test_saves_it_and_goes_on_to_the_verdict(self, state):
        await save_defect(state, DefectData())
        scene = SeverityScene(wizard=AsyncMock())

        await scene.receive(make_callback(), SeverityCB(value="high"), state)

        assert (await load_defect(state)).severity == "high"
        scene.wizard.goto.assert_awaited_once_with(DefectSG.employee_verdict)

    async def test_an_edit_returns_to_the_summary(self, state):
        await save_defect(state, DefectData())
        await state.update_data({UD_EDITING: True})
        scene = SeverityScene(wizard=AsyncMock())

        await scene.receive(make_callback(), SeverityCB(value="high"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)


class TestVerdictScene:
    async def test_the_screen_asks_for_it(self):
        text, keyboard = await VerdictScene.screen(DefectData(), {})

        assert text.render() == build_ask_verdict_text().render()
        assert keyboard == employee_verdict_keyboard()

    async def test_the_severity_is_listed_above_it(self):
        form = DefectData(severity_label="🟠 High")

        text, _ = await VerdictScene.draw(form, {})

        assert "🌡️ Severity: 🟠 High" in text.render()[0]

    async def test_an_edit_asks_for_it_again(self):
        text, keyboard = await VerdictScene.screen(DefectData(), {UD_EDITING: True})

        assert text.render() == build_edit_verdict_text().render()
        assert keyboard == employee_verdict_keyboard()

    async def test_saves_it_and_goes_on_to_the_summary(self, state):
        """From an Edit as well: the summary is next either way."""
        await save_defect(state, DefectData())
        scene = VerdictScene(wizard=AsyncMock())

        await scene.receive(
            make_callback(), VerdictCB(value=DefectVerdict.REPAIR_NOW), state
        )

        defect = await load_defect(state)
        assert defect.verdict == DefectVerdict.REPAIR_NOW
        assert defect.verdict_label == "🟠 Repair Now"
        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)


class TestResponsibleEmployeeScene:
    async def _seed(self, state, search=""):
        await save_defect(state, DefectData(department="bogie"))
        await state.update_data({UD_RESP_SEARCH: search})

    async def test_the_screen_lists_the_form_department_by_the_search(
        self, state, picker
    ):
        form = DefectData(department="coupler_brake")

        await ResponsibleEmployeeScene.screen(form, {UD_RESP_SEARCH: "bo"})

        picker.count.assert_awaited_once_with("coupler_brake", "bo")
        picker.page.assert_awaited_once_with(
            "coupler_brake", "bo", limit=EMPLOYEE_PAGE_SIZE, offset=0
        )

    async def test_the_screen_numbers_the_first_page_of_all(self, picker):
        total = 2 * EMPLOYEE_PAGE_SIZE + 1
        picker.count.return_value = total

        text, _ = await ResponsibleEmployeeScene.screen(DefectData(), {})

        expected = build_ask_responsible_employee_text(1, 3, total)
        assert text.render() == expected.render()

    async def test_a_search_names_the_query_and_the_matches(self, picker):
        picker.count.return_value = 2

        text, _ = await ResponsibleEmployeeScene.screen(
            DefectData(), {UD_RESP_SEARCH: "Bold"}
        )

        expected = build_responsible_employee_search_text("Bold", 2)
        assert text.render() == expected.render()

    async def test_skip_goes_on_to_the_photo_scene(self, state):
        await self._seed(state)
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.skip(make_callback(), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.photo)

    async def test_skip_records_no_employee(self, state):
        await save_defect(
            state,
            DefectData(responsible_employee_id=5, responsible_employee_label="X Y"),
        )

        await ResponsibleEmployeeScene(wizard=AsyncMock()).skip(make_callback(), state)

        defect = await load_defect(state)
        assert defect.responsible_employee_id is None
        assert defect.responsible_employee_label is None

    async def test_skip_drops_the_search(self, state):
        await self._seed(state, search="foo")

        await ResponsibleEmployeeScene(wizard=AsyncMock()).skip(make_callback(), state)

        assert UD_RESP_SEARCH not in await state.get_data()

    async def test_paging_asks_for_that_page_of_the_department(self, state, picker):
        picker.count.return_value = 3 * EMPLOYEE_PAGE_SIZE
        await self._seed(state, search="bo")

        await ResponsibleEmployeeScene(wizard=AsyncMock()).turn_page(
            make_callback(), ResponsibleEmployeePageCB(page=1), state
        )

        picker.count.assert_awaited_once_with("bogie", "bo")
        picker.page.assert_awaited_once_with(
            "bogie", "bo", limit=EMPLOYEE_PAGE_SIZE, offset=EMPLOYEE_PAGE_SIZE
        )

    async def test_paging_past_the_end_serves_the_last_page(self, state, picker):
        picker.count.return_value = EMPLOYEE_PAGE_SIZE + 1
        await self._seed(state)

        await ResponsibleEmployeeScene(wizard=AsyncMock()).turn_page(
            make_callback(), ResponsibleEmployeePageCB(page=99), state
        )

        assert picker.page.await_args.kwargs["offset"] == EMPLOYEE_PAGE_SIZE

    async def test_paging_redraws_the_list_in_place(self, state, picker):
        await self._seed(state)
        callback = make_callback()
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.turn_page(callback, ResponsibleEmployeePageCB(page=1), state)

        callback.bot.edit_message_text.assert_awaited_once()
        scene.wizard.goto.assert_not_awaited()

    async def test_a_turned_page_keeps_back_under_skip(self, state, picker):
        await self._seed(state)
        callback = make_callback()

        await ResponsibleEmployeeScene(wizard=AsyncMock()).turn_page(
            callback, ResponsibleEmployeePageCB(page=1), state
        )

        keyboard = callback.bot.edit_message_text.await_args.kwargs["reply_markup"]
        bottom = [
            [b.callback_data for b in row] for row in keyboard.inline_keyboard[-3:]
        ]
        assert bottom == [[CB_RESP_EMP_SKIP], [CB_STEP_BACK], [CB_CANCEL]]

    async def test_select_records_the_employee(self, state, picker):
        picker.one.return_value = _make_employee(7, "Bold", "Bat")
        await self._seed(state)
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.select(make_callback(), ResponsibleEmployeeCB(employee_id=7), state)

        picker.one.assert_awaited_once_with(7, "bogie")
        defect = await load_defect(state)
        assert defect.responsible_employee_id == 7
        assert defect.responsible_employee_label == "Bold Bat"
        scene.wizard.goto.assert_awaited_once_with(DefectSG.photo)

    async def test_select_after_an_edit_goes_back_to_the_summary(self, state, picker):
        picker.one.return_value = _make_employee(7, "Bold", "Bat")
        await self._seed(state)
        await state.update_data({UD_EDITING: True})
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.select(make_callback(), ResponsibleEmployeeCB(employee_id=7), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)
        assert (await load_defect(state)).responsible_employee_id == 7

    async def test_select_redraws_the_list_when_the_employee_is_gone(
        self, state, picker
    ):
        await self._seed(state)
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.select(make_callback(), ResponsibleEmployeeCB(employee_id=7), state)

        assert (await load_defect(state)).responsible_employee_id is None
        scene.wizard.retake.assert_awaited_once()
        scene.wizard.goto.assert_not_awaited()

    async def test_select_drops_the_search(self, state, picker):
        picker.one.return_value = _make_employee()
        await self._seed(state, search="query")

        await ResponsibleEmployeeScene(wizard=AsyncMock()).select(
            make_callback(), ResponsibleEmployeeCB(employee_id=1), state
        )

        assert UD_RESP_SEARCH not in await state.get_data()


class TestSearchResponsibleEmployee:
    async def test_stores_the_query_trimmed(self, state):
        await save_defect(state, DefectData(department="bogie"))

        await ResponsibleEmployeeScene(wizard=AsyncMock()).search(
            make_message("  Bold "), state
        )

        assert (await state.get_data())[UD_RESP_SEARCH] == "Bold"

    async def test_draws_the_step_again(self, state):
        """retake() redraws it as a new message; see the flow tests."""
        await save_defect(state, DefectData(department="bogie"))
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.search(make_message("test"), state)

        scene.wizard.retake.assert_awaited_once()

    async def test_all_employees_drops_the_query_and_draws_the_step_again(self, state):
        await save_defect(state, DefectData(department="bogie"))
        await state.update_data({UD_RESP_SEARCH: "Bt"})
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.show_all(make_callback(), state)

        assert UD_RESP_SEARCH not in await state.get_data()
        scene.wizard.retake.assert_awaited_once()


class TestBack:
    HF = DefectData(defect_type=DefectType.HUMAN_FACTOR)
    WEAR = DefectData(defect_type=DefectType.WEAR)

    @pytest.mark.parametrize(
        ("scene", "form", "previous"),
        [
            (WagonScene, WEAR, None),
            (DepartmentScene, WEAR, DefectSG.wagon_num),
            (NodeScene, WEAR, DefectSG.department),
            (PartNumberScene, WEAR, DefectSG.node),
            (DefectTypeScene, WEAR, DefectSG.part_number),
            (ResponsibleEmployeeScene, HF, DefectSG.defect_type),
            (PhotoScene, WEAR, DefectSG.defect_type),
            (PhotoScene, HF, DefectSG.responsible_employee),
            (MeasurementChoiceScene, WEAR, DefectSG.photo),
            (DescriptionScene, WEAR, DefectSG.measurement_choice),
            (DescriptionScene, HF, DefectSG.photo),
            (SeverityScene, WEAR, DefectSG.desc),
            (VerdictScene, WEAR, DefectSG.severity),
            (SummaryScene, WEAR, None),
        ],
    )
    def test_each_step_goes_back_the_way_it_came(self, scene, form, previous):
        assert scene.back_to(form, {}) == previous

    def test_from_an_edit_it_goes_back_to_the_summary(self):
        assert WagonScene.back_to(self.WEAR, {UD_EDITING: True}) == DefectSG.confirm

    def test_a_number_being_asked_for_has_its_own_back(self):
        form = DefectData(current_measurement=THICKNESS)

        assert MeasurementChoiceScene.back_to(form, {}) is None

    async def test_the_screen_gets_back_where_it_leads_somewhere(self):
        _, first = await WagonScene.draw(self.WEAR, {})
        _, second = await DepartmentScene.draw(self.WEAR, {})

        assert first == with_step_buttons(None, back=False)
        assert second == with_step_buttons(department_keyboard(), back=True)

    async def test_the_summary_keeps_its_own_cancel(self):
        form = DefectData(defect_type=DefectType.WEAR)

        _, keyboard = await SummaryScene.draw(form, {})

        assert keyboard == confirm_keyboard(form)

    async def test_back_goes_to_the_previous_step_and_keeps_the_form(self, state):
        await save_defect(state, DefectData(department="bogie", node="wheel"))
        scene = NodeScene(wizard=AsyncMock())

        await scene.step_back(make_callback(), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.department)
        assert (await load_defect(state)).node == "wheel"

    async def test_back_from_the_first_step_does_nothing(self, state):
        await save_defect(state, DefectData())
        scene = WagonScene(wizard=AsyncMock())

        await scene.step_back(make_callback(), state)

        scene.wizard.goto.assert_not_awaited()


class TestSummaryScene:
    async def test_the_screen_is_the_whole_form_and_its_buttons(self):
        form = DefectData(wagon_number="60123456", severity_label="High")

        text, keyboard = await SummaryScene.draw(form, {})

        rendered = text.render()[0]
        assert rendered.startswith(build_review_heading().render()[0])
        assert "🚃 Wagon: 60123456" in rendered
        assert "🔢 Part number: —" in rendered
        assert rendered.endswith(build_save_question_text().render()[0])
        assert keyboard == confirm_keyboard(form)

    async def test_entering_it_ends_an_edit(self, state):
        await save_defect(state, DefectData())
        await state.update_data({UD_EDITING: True})
        callback = make_callback()

        await SummaryScene(wizard=AsyncMock()).show_as_edit(callback, state)

        assert UD_EDITING not in await state.get_data()
        callback.bot.edit_message_text.assert_awaited_once()

    async def test_edit_enters_the_fields_scene_in_edit_mode(self, state):
        """The scene draws the edit prompt; see the flow tests."""
        await save_defect(state, DefectData(department="bogie"))
        scene = SummaryScene(wizard=AsyncMock())

        await scene.edit(make_callback(), EditCB(field="node"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.node)
        assert (await state.get_data())[UD_EDITING] is True

    async def test_edit_responsible_opens_its_list(self, state):
        await save_defect(state, DefectData(defect_type=DefectType.HUMAN_FACTOR))
        scene = SummaryScene(wizard=AsyncMock())

        await scene.edit(make_callback(), EditCB(field=EDIT_RESPONSIBLE), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.responsible_employee)

    async def test_an_older_summary_cannot_give_another_type_an_employee(self, state):
        """Its Responsible button outlives a change of type to one without."""
        await save_defect(state, DefectData(defect_type=DefectType.WEAR))
        scene = SummaryScene(wizard=AsyncMock())

        await scene.edit(make_callback(), EditCB(field=EDIT_RESPONSIBLE), state)

        scene.wizard.goto.assert_not_awaited()
        assert UD_EDITING not in await state.get_data()

    async def test_edit_photos_and_measurements_open_their_steps(self, state):
        await save_defect(state, DefectData(defect_type=DefectType.WEAR))

        for field, step in (
            ("photos", DefectSG.photo),
            (EDIT_MEASUREMENTS, DefectSG.measurement_choice),
        ):
            scene = SummaryScene(wizard=AsyncMock())
            await scene.edit(make_callback(), EditCB(field=field), state)
            scene.wizard.goto.assert_awaited_once_with(step)

    async def test_an_older_summary_cannot_give_a_human_factor_measurements(
        self, state
    ):
        """Its Measurements button outlives a change of type to a human factor."""
        await save_defect(state, DefectData(defect_type=DefectType.HUMAN_FACTOR))
        scene = SummaryScene(wizard=AsyncMock())

        await scene.edit(make_callback(), EditCB(field=EDIT_MEASUREMENTS), state)

        scene.wizard.goto.assert_not_awaited()

    async def test_an_unknown_field_is_ignored(self, state):
        await save_defect(state, DefectData())
        scene = SummaryScene(wizard=AsyncMock())

        await scene.edit(make_callback(), EditCB(field="nope"), state)

        scene.wizard.goto.assert_not_awaited()
        assert UD_EDITING not in await state.get_data()

    async def test_declining_cancels_the_form(self):
        callback = make_callback()
        scene = SummaryScene(wizard=AsyncMock())

        await scene.decline(callback)

        scene.wizard.exit.assert_awaited_once()
        sent = callback.bot.send_message.await_args.kwargs
        assert (sent["text"], sent["reply_markup"]) == (
            str(M.DEFECT_CANCELLED),
            main_menu_keyboard(),
        )


class TestUnlinkedEmployeeIsRefused:
    """What the web revokes, the bot stops honouring — including mid-flow."""

    async def test_the_save_saves_nothing_without_an_employee(self, state, bot):
        from apps.bot.handlers.defect.confirm import SavingScene

        await save_defect(state, DefectData(wagon_id=1))
        scene = SavingScene(wizard=AsyncMock())
        callback = make_callback()

        with patch(
            "apps.bot.handlers.defect.confirm.handler.persist_defect",
            AsyncMock(),
        ) as persist:
            await scene.save(callback, state, bot, None)

        persist.assert_not_called()
        callback.answer.assert_awaited_once_with()
        sent = callback.bot.edit_message_text.await_args.kwargs
        assert sent["text"] == build_not_registered_text().render()[0]
        scene.wizard.exit.assert_awaited_once()


class TestAfterPhotos:
    async def test_human_factor_skips_the_measurements(self, state):
        """Its employee was asked right after the type."""
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.HUMAN_FACTOR)
        await save_defect(state, defect)
        scene = PhotoScene(wizard=AsyncMock())

        await after_photos(scene, defect, state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.desc)

    async def test_other_defect_types_go_to_the_measurement_scene(self, state):
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.WEAR)
        await save_defect(state, defect)
        scene = PhotoScene(wizard=AsyncMock())

        await after_photos(scene, defect, state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.measurement_choice)

    async def test_an_edit_goes_back_to_the_summary(self, state):
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.WEAR)
        await save_defect(state, defect)
        await state.update_data({UD_EDITING: True})
        scene = PhotoScene(wizard=AsyncMock())

        await after_photos(scene, defect, state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)


class TestEditingThePhotos:
    PHOTO = PhotoEntry(file_id="AgAC", message_id=10)

    async def test_the_screen_counts_them_and_offers_clear(self):
        form = DefectData(photos=[self.PHOTO])

        text, keyboard = await PhotoScene.screen(form, {UD_EDITING: True})

        assert text.render() == build_edit_photos_text(any_attached=True).render()
        assert keyboard == clear_or_done_keyboard(CB_PHOTO_CLEAR, CB_PHOTO_SKIP)

    async def test_with_none_it_offers_skip(self):
        text, keyboard = await PhotoScene.screen(DefectData(), {UD_EDITING: True})

        assert text.render() == build_edit_photos_text(any_attached=False).render()
        assert keyboard == skip_keyboard(CB_PHOTO_SKIP)

    async def test_clear_drops_them_and_asks_again_in_place(self, state):
        await save_defect(state, DefectData(photos=[self.PHOTO]))
        await state.update_data({UD_EDITING: True})
        callback = make_callback()

        await PhotoScene(wizard=AsyncMock()).clear(callback, state)

        assert (await load_defect(state)).photos == []
        callback.bot.edit_message_text.assert_awaited_once()


THICKNESS = MeasurementEntry(
    dimension="thickness", dimension_label="Thickness", unit="mm"
)


class TestMeasurementChoiceScene:
    async def test_before_any_the_card_offers_the_dimensions_and_skip(self):
        text, keyboard = await MeasurementChoiceScene.screen(DefectData(), {})

        assert text.render() == build_ask_measurement_text(any_saved=False).render()
        assert keyboard == measurement_keyboard(any_saved=False)

    async def test_the_fields_list_what_is_saved_and_the_card_offers_done(self):
        form = DefectData(
            measurements=[
                MeasurementEntry(dimension_label="Width", value=3.0),
                THICKNESS.model_copy(update={"value": 12.5}),
            ]
        )

        text, _ = await MeasurementChoiceScene.draw(form, {})
        _, keyboard = await MeasurementChoiceScene.screen(form, {})

        rendered = text.render()[0]
        assert "📐 Measurements: 2\n🔹 Width: 3.0\n🔹 Thickness: 12.5 mm" in rendered
        assert keyboard == measurement_keyboard(any_saved=True)

    async def test_a_picked_dimension_asks_for_its_number(self):
        form = DefectData(current_measurement=THICKNESS)

        text, keyboard = await MeasurementChoiceScene.screen(form, {})

        assert text.render() == build_ask_value_text("Thickness", "mm").render()
        assert keyboard == measurement_value_keyboard()

    def test_the_prompt_names_the_unit_when_there_is_one(self):
        assert (
            build_ask_value_text("Thickness", "mm")
            .render()[0]
            .startswith("📏 Thickness, mm\n")
        )
        assert build_ask_value_text("Other", "").render()[0].startswith("📏 Other\n")

    async def test_a_dimension_is_held_with_its_unit_and_asked_in_place(self, state):
        await save_defect(state, DefectData())
        callback = make_callback()

        await MeasurementChoiceScene(wizard=AsyncMock()).pick(
            callback, DimensionCB(value="thickness"), state
        )

        assert (await load_defect(state)).current_measurement == THICKNESS
        callback.bot.edit_message_text.assert_awaited_once()

    async def test_other_has_no_unit(self, state):
        await save_defect(state, DefectData())

        await MeasurementChoiceScene(wizard=AsyncMock()).pick(
            make_callback(), DimensionCB(value="other"), state
        )

        assert (await load_defect(state)).current_measurement.unit == ""

    async def test_back_drops_the_picked_dimension(self, state):
        await save_defect(state, DefectData(current_measurement=THICKNESS))
        callback = make_callback()

        await MeasurementChoiceScene(wizard=AsyncMock()).back(callback, state)

        assert (await load_defect(state)).current_measurement is None
        callback.bot.edit_message_text.assert_awaited_once()

    async def test_the_number_is_saved_and_the_card_shown_again(self, state):
        await save_defect(state, DefectData(current_measurement=THICKNESS))
        message = make_message("12,5")

        await MeasurementChoiceScene(wizard=AsyncMock()).receive(message, state)

        defect = await load_defect(state)
        assert defect.measurements == [THICKNESS.model_copy(update={"value": 12.5})]
        assert defect.current_measurement is None
        message.delete.assert_awaited_once()
        reply_markup = message.bot.send_message.await_args.kwargs["reply_markup"]
        assert reply_markup == with_step_buttons(
            measurement_keyboard(any_saved=True), back=True
        )

    async def test_a_non_number_is_named_on_the_prompt(self, state):
        await save_defect(state, DefectData(current_measurement=THICKNESS))
        message = make_message("twelve")

        await MeasurementChoiceScene(wizard=AsyncMock()).receive(message, state)

        defect = await load_defect(state)
        assert defect.measurements == []
        assert defect.current_measurement == THICKNESS
        message.delete.assert_awaited_once()
        notice = build_value_invalid_text("twelve")
        content, keyboard = await MeasurementChoiceScene.draw(defect, {}, notice=notice)
        sent = message.bot.send_message.await_args.kwargs
        assert (sent["text"], sent["entities"]) == content.render()
        assert sent["reply_markup"] == keyboard
        assert keyboard == with_step_buttons(measurement_value_keyboard(), back=False)

    async def test_text_before_a_dimension_shows_the_card_again(self, state):
        await save_defect(state, DefectData())
        message = make_message("12")

        await MeasurementChoiceScene(wizard=AsyncMock()).receive(message, state)

        assert (await load_defect(state)).measurements == []
        message.delete.assert_awaited_once()
        reply_markup = message.bot.send_message.await_args.kwargs["reply_markup"]
        assert reply_markup == with_step_buttons(
            measurement_keyboard(any_saved=False), back=True
        )

    async def test_done_moves_on_to_the_description_scene(self, state):
        scene = MeasurementChoiceScene(wizard=AsyncMock())

        await scene.done(make_callback(), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.desc)

    async def test_an_edit_offers_clear_and_done_goes_back(self, state):
        form = DefectData(measurements=[THICKNESS.model_copy(update={"value": 1.0})])
        await save_defect(state, form)
        await state.update_data({UD_EDITING: True})
        scene = MeasurementChoiceScene(wizard=AsyncMock())

        _, keyboard = await MeasurementChoiceScene.screen(form, {UD_EDITING: True})
        await scene.done(make_callback(), state)

        assert keyboard == measurement_keyboard(any_saved=True, clearable=True)
        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)

    async def test_clear_drops_them_and_shows_the_card_in_place(self, state):
        form = DefectData(
            measurements=[THICKNESS.model_copy(update={"value": 1.0})],
            current_measurement=THICKNESS,
        )
        await save_defect(state, form)
        callback = make_callback()

        await MeasurementChoiceScene(wizard=AsyncMock()).clear(callback, state)

        defect = await load_defect(state)
        assert defect.measurements == []
        assert defect.current_measurement is None
        callback.bot.edit_message_text.assert_awaited_once()


class TestDescriptionScene:
    async def test_the_screen_asks_for_it_with_skip(self):
        text, keyboard = await DescriptionScene.screen(DefectData(), {})

        assert text.render() == build_ask_description_text().render()
        assert keyboard == skip_keyboard(CB_DESC_SKIP)

    async def test_an_edit_asks_for_it_again(self):
        text, keyboard = await DescriptionScene.screen(DefectData(), {UD_EDITING: True})

        assert text.render() == build_edit_description_text().render()
        assert keyboard == skip_keyboard(CB_DESC_SKIP)

    async def test_a_typed_one_is_saved_and_the_severity_asked(self, state):
        await save_defect(state, DefectData())
        scene = DescriptionScene(wizard=AsyncMock())

        await scene.receive(make_message("  Cracked weld  "), state)

        assert (await load_defect(state)).description == "Cracked weld"
        scene.wizard.goto.assert_awaited_once_with(DefectSG.severity)

    async def test_a_longer_one_stays_and_the_screen_goes_under_it(self, state):
        """Left in the chat, to be copied and shortened."""
        await save_defect(state, DefectData())
        await state.set_state(DefectSG.desc)
        await state.update_data({UD_SCREEN: [CHAT_ID, 7]})
        message = make_message("x" * 1001)

        await DescriptionScene(wizard=AsyncMock()).receive(message, state)

        assert (await load_defect(state)).description == ""
        assert await state.get_state() == DefectSG.desc.state
        message.delete.assert_not_awaited()
        notice = build_description_too_long_text(1001, 1000)
        content, _ = await DescriptionScene.draw(DefectData(), {}, notice=notice)
        sent = message.bot.send_message.await_args.kwargs
        assert (sent["text"], sent["entities"]) == content.render()
        message.bot.delete_message.assert_awaited_once_with(
            chat_id=CHAT_ID, message_id=7
        )
        assert (await state.get_data())[UD_SCREEN] == [CHAT_ID, SENT_ID]

    async def test_skip_clears_it_and_asks_the_severity(self, state):
        await save_defect(state, DefectData(description="Old"))
        scene = DescriptionScene(wizard=AsyncMock())

        await scene.skip(make_callback(), state)

        assert (await load_defect(state)).description == ""
        scene.wizard.goto.assert_awaited_once_with(DefectSG.severity)

    async def test_an_edit_returns_to_the_summary(self, state):
        await save_defect(state, DefectData())
        await state.update_data({UD_EDITING: True})
        scene = DescriptionScene(wizard=AsyncMock())

        await scene.receive(make_message("Cracked weld"), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.confirm)


class TestScreenText:
    """The heading, the form so far, a notice, then the step's question."""

    WEAR = DefectData(defect_type=DefectType.WEAR)
    HF = DefectData(defect_type=DefectType.HUMAN_FACTOR)

    @pytest.mark.usefixtures("picker")
    @pytest.mark.parametrize(
        ("scene", "form", "step"),
        [
            (WagonScene, WEAR, 1),
            (DepartmentScene, WEAR, 2),
            (DefectTypeScene, WEAR, 5),
            (PhotoScene, WEAR, 6),
            (MeasurementChoiceScene, WEAR, 7),
            (ResponsibleEmployeeScene, HF, 6),
            (PhotoScene, HF, 7),
            (DescriptionScene, HF, 8),
            (SeverityScene, HF, 9),
            (VerdictScene, HF, 10),
            (VerdictScene, WEAR, 10),
        ],
    )
    async def test_the_heading_counts_ten_steps_on_either_branch(
        self, scene, form, step
    ):
        text, _ = await scene.draw(form, {})

        assert text.render()[0].startswith(build_step_heading(step, 10).render()[0])

    async def test_a_step_not_reached_yet_is_not_listed(self):
        text, _ = await NodeScene.draw(DefectData(wagon_number="1"), {})

        rendered = text.render()[0]
        assert "🚃 Wagon: 1" in rendered
        assert "Part number" not in rendered
        assert "Severity" not in rendered

    async def test_a_step_behind_that_was_skipped_is_a_dash(self):
        text, _ = await DefectTypeScene.draw(DefectData(wagon_number="1"), {})

        assert "🔢 Part number: —" in text.render()[0]

    async def test_an_answer_kept_after_back_is_still_listed(self):
        form = DefectData(wagon_number="1", severity_label="🟠 High")

        text, _ = await NodeScene.draw(form, {})

        assert "🌡️ Severity: 🟠 High" in text.render()[0]

    async def test_an_edit_lists_the_whole_form(self):
        data = {UD_EDITING: True}

        text, _ = await NodeScene.draw(DefectData(wagon_number="1"), data)

        rendered = text.render()[0]
        assert rendered.startswith(build_editing_heading().render()[0])
        assert "🌡️ Severity: —" in rendered
        assert rendered.endswith(build_edit_node_text().render()[0])

    async def test_a_notice_goes_between_the_form_and_the_question(self):
        notice = build_wagon_not_found_text("0000")
        form = DefectData(wagon_number="1")

        text, _ = await DepartmentScene.draw(form, {}, notice=notice)

        rendered = text.render()[0]
        question = build_ask_department_text().render()[0]
        assert rendered.index("Wagon: 1") < rendered.index("0000")
        assert rendered.endswith(question)

    async def test_measurements_are_listed_under_their_count(self):
        gap = MeasurementEntry(dimension_label="Gap", value=3.0, unit="mm")

        text, _ = await SummaryScene.draw(DefectData(measurements=[gap]), {})

        assert "📐 Measurements: 1\n🔹 Gap: 3.0 mm" in text.render()[0]


class TestUserTextIsEscaped:
    """Replies go out as HTML: text the bot did not write must not parse as tags."""

    async def test_the_search_query(self, picker):
        """An entity, not HTML: the query goes out as typed."""
        form = DefectData(department="bogie")

        text, _ = await ResponsibleEmployeeScene.screen(form, {UD_RESP_SEARCH: "<b"})

        assert "<b>&lt;b</b>" in html_decoration.unparse(*text.render())

    async def test_what_the_summary_repeats(self):
        """Entities, not HTML: the part number and description go out as typed."""
        form = DefectData(part_number="<PN&1>", description="<b>weld</b>")

        text, _ = await SummaryScene.draw(form, {})
        html = html_decoration.unparse(*text.render())

        assert "<b>&lt;PN&amp;1&gt;</b>" in html
        assert "Description: &lt;b&gt;weld&lt;/b&gt;" in html

    async def test_the_responsible_employee_is_shown_as_stored(self, state, picker):
        """An entity, not HTML: the name goes out verbatim."""
        picker.one.return_value = _make_employee(7, "<b>Bold", "Bat")
        await save_defect(
            state, DefectData(department="bogie", defect_type=DefectType.HUMAN_FACTOR)
        )

        await ResponsibleEmployeeScene(wizard=AsyncMock()).select(
            make_callback(), ResponsibleEmployeeCB(employee_id=7), state
        )
        form = await load_defect(state)
        text, _ = await PhotoScene.draw(form, {})

        assert form.responsible_employee_label == "<b>Bold Bat"
        assert "<b>Bold Bat" in text.render()[0]

    async def test_the_employee_name_in_the_greeting(self):
        """Sent as entities rather than HTML, so the name goes out verbatim."""
        from apps.bot.handlers.start.start import show_welcome_menu

        employee = MagicMock(full_name="A & <B>", role="inspector")
        employee.get_role_display.return_value = "Inspector"
        message = make_message()

        await show_welcome_menu(message, employee)

        sent = message.answer.await_args.kwargs
        assert sent["parse_mode"] is None
        html = html_decoration.unparse(sent["text"], sent["entities"])
        assert "<b>A &amp; &lt;B&gt;</b>" in html
