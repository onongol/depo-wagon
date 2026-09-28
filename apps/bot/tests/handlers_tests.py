"""Tests for the defect registration steps and the shared utility handlers.

Every step now round-trips its form through storage, so a loaded DefectData is
a detached copy — the assertions read it back rather than holding a reference.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.utils.text_decorations import html_decoration

from apps.bot.callback_data import (
    CB_DESC_SKIP,
    DefectTypeCB,
    DepartmentCB,
    EditCB,
    NodeCB,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
    SeverityCB,
)
from apps.bot.constants import (
    BTN_ASK,
    BTN_CANCEL,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
    BTN_SAVE,
    UD_DEFECT,
    UD_EDITING,
    UD_RESP_SEARCH,
)
from apps.bot.fsm import load_defect, save_defect
from apps.bot.handlers.common.cancel import cancel
from apps.bot.handlers.common.help import help_command
from apps.bot.handlers.common.text import build_cancelled_text, build_help_text
from apps.bot.handlers.defect.defect_type import DefectTypeScene
from apps.bot.handlers.defect.department import DepartmentScene
from apps.bot.handlers.defect.description import receive_description
from apps.bot.handlers.defect.edit import start_edit
from apps.bot.handlers.defect.node import NodeScene
from apps.bot.handlers.defect.part_number import (
    PART_NUMBER_MAX_LENGTH,
    PartNumberScene,
)
from apps.bot.handlers.defect.responsible_employee import ResponsibleEmployeeScene
from apps.bot.handlers.defect.responsible_employee.list import EMPLOYEE_PAGE_SIZE
from apps.bot.handlers.defect.severity import SeverityScene
from apps.bot.handlers.defect.start import new_defect_start
from apps.bot.handlers.defect.text import (
    build_ask_measurement_text,
    build_ask_responsible_employee_text,
    build_defect_type_confirmed_text,
    build_part_number_confirmed_text,
    build_part_number_skipped_text,
    build_responsible_employee_confirmed_text,
    build_responsible_employee_search_text,
    build_responsible_employee_skipped_text,
    build_wagon_not_found_text,
)
from apps.bot.handlers.defect.wagon import WagonScene
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import severity_keyboard
from apps.bot.keyboards.measurement import measurement_choice_keyboard
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.tests.builders import make_callback, make_message
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectNode, DefectType

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
    async def test_an_unknown_number_is_echoed_as_typed(self, state):
        """An entity, not HTML: markup in what the user typed needs no escaping."""
        await save_defect(state, DefectData())
        message = make_message("<b>80035668</b>")

        with patch(WAGON_LOOKUP, AsyncMock(return_value=None)):
            await WagonScene(wizard=MagicMock()).receive(message, state)

        message.answer.assert_awaited_once_with(
            **build_wagon_not_found_text("<b>80035668</b>").as_kwargs()
        )
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
        callback = make_callback()

        wizard = AsyncMock(event=callback, update_type="callback_query")
        await NodeScene(wizard=wizard).receive(callback, NodeCB(value="wheel"), state)

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()
        callback.message.edit_text.assert_awaited_once()


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

    async def test_a_longer_part_number_is_asked_for_again(self, state):
        await save_defect(state, DefectData())
        scene = PartNumberScene(wizard=AsyncMock())
        message = make_message("x" * (PART_NUMBER_MAX_LENGTH + 1))

        await scene.receive(message, state)

        assert (await load_defect(state)).part_number == ""
        scene.wizard.goto.assert_not_awaited()
        reply = message.answer.await_args.kwargs["text"]
        assert f"{PART_NUMBER_MAX_LENGTH + 1}/{PART_NUMBER_MAX_LENGTH}" in reply

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
        callback = make_callback()
        scene = PartNumberScene(
            wizard=AsyncMock(event=callback, update_type="callback_query")
        )

        await scene.skip(callback, state)

        scene.wizard.goto.assert_not_awaited()
        assert await state.get_state() == DefectSG.confirm.state
        assert (await load_defect(state)).part_number == ""


class TestReceiveDefectType:
    async def test_saves_the_type(self, state):
        await save_defect(state, DefectData())

        await DefectTypeScene(wizard=AsyncMock()).receive(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        assert (await load_defect(state)).defect_type == DefectType.HUMAN_FACTOR

    async def test_every_other_type_goes_on_to_the_severity_scene(self, state):
        """Its screen is the severity scene's to draw; see TestSeverityScene."""
        for value in set(DefectType.values) - {DefectType.HUMAN_FACTOR}:
            await save_defect(state, DefectData())
            scene = DefectTypeScene(wizard=AsyncMock())

            await scene.receive(make_callback(), DefectTypeCB(value=value), state)

            scene.wizard.goto.assert_awaited_once_with(DefectSG.severity)

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

    async def test_the_screen_says_whether_the_part_number_was_skipped(self):
        typed, _ = await DefectTypeScene.screen(DefectData(part_number="PN-1"), {})
        skipped, _ = await DefectTypeScene.screen(DefectData(), {})

        assert "PN-1" in typed.render()[0]
        assert skipped.render() == build_part_number_skipped_text().render()

    async def test_the_part_number_is_shown_as_typed(self, state):
        """An entity, not HTML: markup in what the user typed needs no escaping."""
        await save_defect(state, DefectData())

        await PartNumberScene(wizard=AsyncMock()).receive(make_message("<A&B>"), state)
        form = await load_defect(state)
        text, _ = await DefectTypeScene.screen(form, {})

        assert form.part_number == "<A&B>"
        assert text.render() == build_part_number_confirmed_text("<A&B>").render()


class TestSeverityScene:
    async def test_the_screen_names_the_type_and_offers_the_levels(self):
        form = DefectData(defect_type_label="Crack")

        text, keyboard = await SeverityScene.screen(form, {})

        assert text.render() == build_defect_type_confirmed_text("Crack").render()
        assert keyboard == severity_keyboard()

    async def test_after_a_human_factor_the_screen_names_the_employee(self):
        form = DefectData(
            defect_type=DefectType.HUMAN_FACTOR, responsible_employee_label="Bold Bat"
        )

        text, _ = await SeverityScene.screen(form, {})

        expected = build_responsible_employee_confirmed_text("Bold Bat")
        assert text.render() == expected.render()

    async def test_after_a_human_factor_the_screen_says_it_was_skipped(self):
        form = DefectData(defect_type=DefectType.HUMAN_FACTOR)

        text, _ = await SeverityScene.screen(form, {})

        assert text.render() == build_responsible_employee_skipped_text().render()

    async def test_an_edit_asks_for_it_again(self):
        text, keyboard = await SeverityScene.screen(DefectData(), {UD_EDITING: True})

        assert text == str(M.EDIT_SEVERITY)
        assert keyboard == severity_keyboard()

    async def test_saves_it_and_goes_on_to_the_photo_scene(self, state):
        await save_defect(state, DefectData())
        scene = SeverityScene(wizard=AsyncMock())

        await scene.receive(make_callback(), SeverityCB(value="high"), state)

        assert (await load_defect(state)).severity == "high"
        scene.wizard.goto.assert_awaited_once_with(DefectSG.photo)

    async def test_an_edit_goes_back_to_the_summary(self, state):
        await save_defect(state, DefectData())
        await state.update_data({UD_EDITING: True})
        callback = make_callback()
        wizard = AsyncMock(event=callback, update_type="callback_query")

        await SeverityScene(wizard=wizard).receive(
            callback, SeverityCB(value="high"), state
        )

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()


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

    async def test_skip_goes_on_to_the_severity_scene(self, state):
        await self._seed(state)
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.skip(make_callback(), state)

        scene.wizard.goto.assert_awaited_once_with(DefectSG.severity)

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

    async def test_select_records_the_employee(self, state, picker):
        picker.one.return_value = _make_employee(7, "Bold", "Bat")
        await self._seed(state)
        scene = ResponsibleEmployeeScene(wizard=AsyncMock())

        await scene.select(make_callback(), ResponsibleEmployeeCB(employee_id=7), state)

        picker.one.assert_awaited_once_with(7, "bogie")
        defect = await load_defect(state)
        assert defect.responsible_employee_id == 7
        assert defect.responsible_employee_label == "Bold Bat"
        scene.wizard.goto.assert_awaited_once_with(DefectSG.severity)

    async def test_select_after_an_edit_goes_back_to_the_summary(self, state, picker):
        picker.one.return_value = _make_employee(7, "Bold", "Bat")
        await self._seed(state)
        await state.update_data({UD_EDITING: True})
        callback = make_callback()
        scene = ResponsibleEmployeeScene(
            wizard=AsyncMock(event=callback, update_type="callback_query")
        )

        await scene.select(callback, ResponsibleEmployeeCB(employee_id=7), state)

        scene.wizard.goto.assert_not_awaited()
        assert await state.get_state() == DefectSG.confirm.state
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


class TestEditFromSummary:
    async def test_routes_to_the_field_and_flags_edit_mode(self, state):
        await save_defect(state, DefectData())

        await start_edit(
            make_callback(), EditCB(field="description"), state, AsyncMock()
        )

        assert (await state.get_data())[UD_EDITING] is True
        assert await state.get_state() == DefectSG.desc.state

    async def test_a_field_that_is_a_scene_is_entered_as_one(self, state):
        """The scene draws the edit prompt; see the flow tests."""
        await save_defect(state, DefectData(department="bogie"))
        scenes = AsyncMock()

        await start_edit(make_callback(), EditCB(field="node"), state, scenes)

        scenes.enter.assert_awaited_once_with(DefectSG.node)
        assert (await state.get_data())[UD_EDITING] is True

    async def test_an_unknown_field_returns_to_the_summary(self, state):
        await save_defect(state, DefectData())

        await start_edit(make_callback(), EditCB(field="nope"), state, AsyncMock())

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()

    async def test_the_edited_field_returns_to_the_summary(self, state):
        await save_defect(state, DefectData())
        await start_edit(
            make_callback(), EditCB(field="description"), state, AsyncMock()
        )

        await receive_description(make_message("Cracked weld"), state)

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()


class TestUnlinkedEmployeeIsRefused:
    """What the web revokes, the bot stops honouring — including mid-flow."""

    async def test_confirm_saves_nothing_without_an_employee(self, state, bot):
        from apps.bot.handlers.defect.confirm import confirm_defect

        await save_defect(state, DefectData(wagon_id=1))

        with patch(
            "apps.bot.handlers.defect.confirm.handler.register_defect",
            AsyncMock(),
        ) as register:
            await confirm_defect(make_callback(), state, bot, None)

        register.assert_not_called()
        assert await state.get_state() is None

    async def test_verdict_is_not_recorded_without_an_employee(self, state, bot):
        from apps.bot.callback_data import VerdictCB
        from apps.bot.handlers.defect.verdict import receive_employee_verdict
        from apps.defects.constants import DefectVerdict

        await save_defect(state, DefectData(defect_id="1"))

        with patch("apps.bot.handlers.defect.verdict.services") as svc:
            await receive_employee_verdict(
                make_callback(),
                VerdictCB(value=DefectVerdict.DECOMMISSION),
                state,
                bot,
                None,
            )

        svc.save_employee_verdict.assert_not_called()
        assert await state.get_state() is None


class TestAfterPhotos:
    async def test_human_factor_skips_the_measurements(self, state):
        """Its employee was asked right after the type."""
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.HUMAN_FACTOR)
        await save_defect(state, defect)
        send = AsyncMock()

        await after_photos(send, defect, state)

        assert await state.get_state() == DefectSG.desc.state
        send.assert_awaited_once_with(
            str(M.ASK_DESCRIPTION),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_DESC_SKIP),
        )

    async def test_other_defect_types_go_to_the_measurement_step(self, state):
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.WEAR)
        await save_defect(state, defect)
        send = AsyncMock()

        await after_photos(send, defect, state)

        assert await state.get_state() == DefectSG.measurement_choice.state
        send.assert_awaited_once_with(
            **build_ask_measurement_text().as_kwargs(),
            reply_markup=measurement_choice_keyboard(),
        )


class TestMeasurementChoice:
    async def test_add_starts_a_measurement_and_asks_for_the_dimension(self, state):
        from apps.bot.handlers.defect.measurement import measurement_add
        from apps.bot.user_data import MeasurementEntry

        await save_defect(state, DefectData())
        callback = make_callback()

        await measurement_add(callback, state)

        assert (await load_defect(state)).current_measurement == MeasurementEntry()
        assert await state.get_state() == DefectSG.measurement_dimension.state
        callback.answer.assert_awaited_once()

    async def test_done_moves_on_to_the_description(self, state):
        from apps.bot.handlers.defect.measurement import measurement_done

        await save_defect(state, DefectData())

        await measurement_done(make_callback(), state)

        assert await state.get_state() == DefectSG.desc.state

    async def test_done_does_not_need_a_form_in_state(self, state):
        from apps.bot.handlers.defect.measurement import measurement_done

        await measurement_done(make_callback(), state)

        assert await state.get_state() == DefectSG.desc.state


class TestMeasurementUnit:
    async def _receive(self, state, text):
        from apps.bot.handlers.defect.measurement import receive_unit
        from apps.bot.user_data import MeasurementEntry

        await save_defect(
            state,
            DefectData(
                current_measurement=MeasurementEntry(dimension_label="Width", value=1.0)
            ),
        )
        await state.set_state(DefectSG.measurement_unit)
        message = make_message(text)
        await receive_unit(message, state)
        return message

    async def test_a_unit_at_the_column_limit_is_saved(self, state):
        from apps.bot.handlers.defect.measurement.unit import MAX_UNIT_LENGTH

        await self._receive(state, "x" * MAX_UNIT_LENGTH)

        assert (await load_defect(state)).measurements[0].unit == "x" * MAX_UNIT_LENGTH
        assert await state.get_state() == DefectSG.measurement_choice.state

    async def test_a_longer_unit_is_asked_for_again(self, state):
        from apps.bot.handlers.defect.measurement.unit import MAX_UNIT_LENGTH

        message = await self._receive(state, "x" * (MAX_UNIT_LENGTH + 1))

        defect = await load_defect(state)
        assert defect.measurements == []
        assert defect.current_measurement is not None
        assert await state.get_state() == DefectSG.measurement_unit.state
        reply = message.answer.await_args.args[0]
        assert f"{MAX_UNIT_LENGTH + 1}/{MAX_UNIT_LENGTH}" in reply

    async def test_surrounding_whitespace_does_not_count(self, state):
        from apps.bot.handlers.defect.measurement.unit import MAX_UNIT_LENGTH

        await self._receive(state, f"  {'x' * MAX_UNIT_LENGTH}  ")

        assert (await load_defect(state)).measurements[0].unit == "x" * MAX_UNIT_LENGTH


class TestUserTextIsEscaped:
    """Replies go out as HTML: text the bot did not write must not parse as tags."""

    async def test_the_search_query(self, picker):
        """An entity, not HTML: the query goes out as typed."""
        form = DefectData(department="bogie")

        text, _ = await ResponsibleEmployeeScene.screen(form, {UD_RESP_SEARCH: "<b"})

        assert "<b>&lt;b</b>" in html_decoration.unparse(*text.render())

    async def test_the_unit_is_escaped_but_stored_as_typed(self, state):
        from apps.bot.handlers.defect.measurement import receive_unit
        from apps.bot.user_data import MeasurementEntry

        await save_defect(
            state,
            DefectData(
                current_measurement=MeasurementEntry(dimension_label="Width", value=1.0)
            ),
        )
        message = make_message("<mm>")

        await receive_unit(message, state)

        assert "&lt;mm&gt;" in message.answer.await_args.args[0]
        assert (await load_defect(state)).measurements[0].unit == "<mm>"

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
        text, _ = await SeverityScene.screen(form, {})

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
