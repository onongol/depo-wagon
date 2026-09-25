"""Tests for the defect registration steps and the shared utility handlers.

Every step now round-trips its form through storage, so a loaded DefectData is
a detached copy — the assertions read it back rather than holding a reference.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.utils.text_decorations import html_decoration

from apps.bot.callback_data import (
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
from apps.bot.handlers.defect.defect_type import receive_defect_type
from apps.bot.handlers.defect.department import receive_department
from apps.bot.handlers.defect.edit import start_edit
from apps.bot.handlers.defect.node import receive_node
from apps.bot.handlers.defect.part_number import (
    PART_NUMBER_MAX_LENGTH,
    receive_part_number,
    skip_part_number,
)
from apps.bot.handlers.defect.responsible_employee import (
    page_responsible_employee,
    search_responsible_employee,
    select_responsible_employee,
    skip_responsible_employee,
)
from apps.bot.handlers.defect.responsible_employee.list import EMPLOYEE_PAGE_SIZE
from apps.bot.handlers.defect.start import new_defect_start
from apps.bot.handlers.defect.text import (
    build_wagon_confirmed_text,
    build_wagon_not_found_text,
)
from apps.bot.handlers.defect.wagon import WagonScene
from apps.bot.keyboards.defect import department_keyboard
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.states import DefectSG
from apps.bot.tests.builders import make_callback, make_message
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectType

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

    async def test_a_known_number_moves_to_the_department_step(self, state):
        await save_defect(state, DefectData())
        message = make_message("80035668")
        wagon = MagicMock(id=3, number="80035668")

        with patch(WAGON_LOOKUP, AsyncMock(return_value=wagon)):
            await WagonScene(wizard=MagicMock()).receive(message, state)

        message.answer.assert_awaited_once_with(
            **build_wagon_confirmed_text("80035668").as_kwargs(),
            reply_markup=department_keyboard(),
        )
        assert await state.get_state() == DefectSG.department.state
        assert (await load_defect(state)).wagon_id == 3


class TestReceiveDepartment:
    async def test_saves_department_and_its_label(self, state):
        await save_defect(state, DefectData())

        await receive_department(make_callback(), DepartmentCB(value="bogie"), state)

        defect = await load_defect(state)
        assert defect.department == "bogie"
        assert defect.department_label

    async def test_moves_to_the_node_step(self, state):
        await save_defect(state, DefectData())

        await receive_department(make_callback(), DepartmentCB(value="bogie"), state)

        assert await state.get_state() == DefectSG.node.state

    async def test_edits_the_message_in_place(self, state):
        await save_defect(state, DefectData())
        callback = make_callback()

        await receive_department(callback, DepartmentCB(value="bogie"), state)

        callback.message.edit_text.assert_awaited_once()


class TestReceiveNode:
    async def test_saves_node_and_its_label(self, state):
        await save_defect(state, DefectData())

        await receive_node(make_callback(), NodeCB(value="wheel"), state)

        defect = await load_defect(state)
        assert defect.node == "wheel"
        assert defect.node_label

    async def test_moves_to_the_part_number_step(self, state):
        await save_defect(state, DefectData())

        await receive_node(make_callback(), NodeCB(value="wheel"), state)

        assert await state.get_state() == DefectSG.part_number.state


class TestReceivePartNumber:
    async def test_text_input_saves_the_part_number(self, state):
        await save_defect(state, DefectData())

        await receive_part_number(make_message("ABC-1234"), state)

        assert (await load_defect(state)).part_number == "ABC-1234"

    async def test_text_input_moves_to_the_defect_type_step(self, state):
        await save_defect(state, DefectData())

        await receive_part_number(make_message("P-001"), state)

        assert await state.get_state() == DefectSG.defect_type.state

    async def test_a_part_number_at_the_column_limit_is_saved(self, state):
        await save_defect(state, DefectData())

        await receive_part_number(make_message("x" * PART_NUMBER_MAX_LENGTH), state)

        assert (await load_defect(state)).part_number == "x" * PART_NUMBER_MAX_LENGTH
        assert await state.get_state() == DefectSG.defect_type.state

    async def test_a_longer_part_number_is_asked_for_again(self, state):
        await save_defect(state, DefectData())
        await state.set_state(DefectSG.part_number)
        message = make_message("x" * (PART_NUMBER_MAX_LENGTH + 1))

        await receive_part_number(message, state)

        assert (await load_defect(state)).part_number == ""
        assert await state.get_state() == DefectSG.part_number.state
        reply = message.answer.await_args.args[0]
        assert f"{PART_NUMBER_MAX_LENGTH + 1}/{PART_NUMBER_MAX_LENGTH}" in reply

    async def test_skip_clears_the_part_number(self, state):
        await save_defect(state, DefectData(part_number="old"))

        await skip_part_number(make_callback(), state)

        assert (await load_defect(state)).part_number == ""

    async def test_skip_moves_to_the_defect_type_step(self, state):
        await save_defect(state, DefectData())

        await skip_part_number(make_callback(), state)

        assert await state.get_state() == DefectSG.defect_type.state


class TestReceiveDefectType:
    async def test_saves_the_type_and_moves_to_severity(self, state):
        await save_defect(state, DefectData())

        await receive_defect_type(
            make_callback(), DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        assert (await load_defect(state)).defect_type == DefectType.HUMAN_FACTOR
        assert await state.get_state() == DefectSG.severity.state

    async def test_offers_the_severity_keyboard(self, state):
        await save_defect(state, DefectData())
        callback = make_callback()

        await receive_defect_type(
            callback, DefectTypeCB(value=DefectType.HUMAN_FACTOR), state
        )

        kb = callback.message.edit_text.await_args.kwargs["reply_markup"]
        payloads = [b.callback_data for row in kb.inline_keyboard for b in row]
        assert any(p.startswith(SeverityCB.__prefix__ + ":") for p in payloads)

    async def test_every_type_reaches_the_same_step(self, state):
        for value in DefectType.values:
            await save_defect(state, DefectData())
            await receive_defect_type(make_callback(), DefectTypeCB(value=value), state)
            assert await state.get_state() == DefectSG.severity.state


class TestResponsibleEmployee:
    async def _seed(self, state, search=""):
        await save_defect(state, DefectData(department="bogie"))
        await state.update_data({UD_RESP_SEARCH: search})

    async def test_skip_moves_to_the_description(self, state):
        await self._seed(state)

        await skip_responsible_employee(make_callback(), state)

        assert await state.get_state() == DefectSG.desc.state

    async def test_skip_records_no_employee(self, state):
        await save_defect(
            state,
            DefectData(responsible_employee_id=5, responsible_employee_label="X Y"),
        )

        await skip_responsible_employee(make_callback(), state)

        defect = await load_defect(state)
        assert defect.responsible_employee_id is None
        assert defect.responsible_employee_label is None

    async def test_skip_drops_the_search(self, state):
        await self._seed(state, search="foo")

        await skip_responsible_employee(make_callback(), state)

        assert UD_RESP_SEARCH not in await state.get_data()

    async def test_paging_asks_for_that_page_of_the_department(self, state, picker):
        picker.count.return_value = 3 * EMPLOYEE_PAGE_SIZE
        await self._seed(state, search="bo")

        await page_responsible_employee(
            make_callback(), ResponsibleEmployeePageCB(page=1), state
        )

        picker.count.assert_awaited_once_with("bogie", "bo")
        picker.page.assert_awaited_once_with(
            "bogie", "bo", limit=EMPLOYEE_PAGE_SIZE, offset=EMPLOYEE_PAGE_SIZE
        )

    async def test_paging_past_the_end_serves_the_last_page(self, state, picker):
        picker.count.return_value = EMPLOYEE_PAGE_SIZE + 1
        await self._seed(state)

        await page_responsible_employee(
            make_callback(), ResponsibleEmployeePageCB(page=99), state
        )

        assert picker.page.await_args.kwargs["offset"] == EMPLOYEE_PAGE_SIZE

    async def test_paging_leaves_the_step_where_it_is(self, state, picker):
        await self._seed(state)
        await state.set_state(DefectSG.responsible_employee)

        await page_responsible_employee(
            make_callback(), ResponsibleEmployeePageCB(page=1), state
        )

        assert await state.get_state() == DefectSG.responsible_employee.state

    async def test_select_records_the_employee(self, state, picker):
        picker.one.return_value = _make_employee(7, "Bold", "Bat")
        await self._seed(state)

        await select_responsible_employee(
            make_callback(), ResponsibleEmployeeCB(employee_id=7), state
        )

        picker.one.assert_awaited_once_with(7, "bogie")
        defect = await load_defect(state)
        assert defect.responsible_employee_id == 7
        assert defect.responsible_employee_label == "Bold Bat"
        assert await state.get_state() == DefectSG.desc.state

    async def test_select_redraws_the_list_when_the_employee_is_gone(
        self, state, picker
    ):
        await self._seed(state)
        await state.set_state(DefectSG.responsible_employee)
        callback = make_callback()

        await select_responsible_employee(
            callback, ResponsibleEmployeeCB(employee_id=7), state
        )

        assert (await load_defect(state)).responsible_employee_id is None
        assert await state.get_state() == DefectSG.responsible_employee.state
        picker.page.assert_awaited_once()
        callback.message.edit_text.assert_awaited_once()

    async def test_select_drops_the_search(self, state, picker):
        picker.one.return_value = _make_employee()
        await self._seed(state, search="query")

        await select_responsible_employee(
            make_callback(), ResponsibleEmployeeCB(employee_id=1), state
        )

        assert UD_RESP_SEARCH not in await state.get_data()


class TestSearchResponsibleEmployee:
    async def _seed(self, state):
        await save_defect(state, DefectData(department="bogie"))

    async def test_stores_the_query(self, state, picker):
        await self._seed(state)

        await search_responsible_employee(make_message("Bold"), state)

        assert (await state.get_data())[UD_RESP_SEARCH] == "Bold"

    async def test_searches_the_department_on_the_form(self, state, picker):
        await self._seed(state)

        await search_responsible_employee(make_message("  Bold "), state)

        picker.count.assert_awaited_once_with("bogie", "Bold")

    async def test_leaves_the_step_where_it_is(self, state, picker):
        await self._seed(state)
        await state.set_state(DefectSG.responsible_employee)

        await search_responsible_employee(make_message("test"), state)

        assert await state.get_state() == DefectSG.responsible_employee.state

    async def test_re_renders_as_a_new_message(self, state, picker):
        await self._seed(state)
        message = make_message("test")

        await search_responsible_employee(message, state)

        message.answer.assert_awaited_once()


class TestEditFromSummary:
    async def test_routes_to_the_field_and_flags_edit_mode(self, state):
        await save_defect(state, DefectData(department="bogie"))

        await start_edit(make_callback(), EditCB(field="node"), state, AsyncMock())

        assert (await state.get_data())[UD_EDITING] is True
        assert await state.get_state() == DefectSG.node.state

    async def test_an_unknown_field_returns_to_the_summary(self, state):
        await save_defect(state, DefectData())

        await start_edit(make_callback(), EditCB(field="nope"), state, AsyncMock())

        assert await state.get_state() == DefectSG.confirm.state
        assert UD_EDITING not in await state.get_data()

    async def test_the_edited_field_returns_to_the_summary(self, state):
        await save_defect(state, DefectData(department="bogie"))
        await start_edit(make_callback(), EditCB(field="node"), state, AsyncMock())

        await receive_node(make_callback(), NodeCB(value="wheel"), state)

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
    async def test_human_factor_opens_the_list_for_the_form_department(
        self, state, picker
    ):
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(
            defect_type=DefectType.HUMAN_FACTOR, department="coupler_brake"
        )
        await save_defect(state, defect)

        await after_photos(AsyncMock(), defect, state)

        picker.count.assert_awaited_once_with("coupler_brake", "")
        assert await state.get_state() == DefectSG.responsible_employee.state

    async def test_a_failed_lookup_keeps_the_photo_step_to_retry(self, state, picker):
        """error_handler answers; Done is still on screen to tap again."""
        from apps.bot.handlers.defect.photo.routing import after_photos

        picker.count.side_effect = RuntimeError("db down")
        defect = DefectData(defect_type=DefectType.HUMAN_FACTOR, department="bogie")
        await save_defect(state, defect)
        await state.set_state(DefectSG.photo)

        with pytest.raises(RuntimeError):
            await after_photos(AsyncMock(), defect, state)

        assert await state.get_state() == DefectSG.photo.state

    async def test_other_defect_types_go_to_the_measurement_step(self, state):
        from apps.bot.handlers.defect.photo.routing import after_photos

        defect = DefectData(defect_type=DefectType.WEAR)
        await save_defect(state, defect)

        await after_photos(AsyncMock(), defect, state)

        assert await state.get_state() == DefectSG.measurement_choice.state


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

    async def test_the_search_query(self, state, picker):
        await save_defect(state, DefectData(department="bogie"))
        message = make_message("<b")

        await search_responsible_employee(message, state)

        assert "&lt;b" in message.answer.await_args.args[0]

    async def test_the_part_number_is_escaped_but_stored_as_typed(self, state):
        await save_defect(state, DefectData())
        message = make_message("<A&B>")

        await receive_part_number(message, state)

        assert "&lt;A&amp;B&gt;" in message.answer.await_args.args[0]
        assert (await load_defect(state)).part_number == "<A&B>"

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

    async def test_the_responsible_employee_is_escaped_but_stored_as_is(
        self, state, picker
    ):
        picker.one.return_value = _make_employee(7, "<b>Bold", "Bat")
        await save_defect(state, DefectData(department="bogie"))
        callback = make_callback()

        await select_responsible_employee(
            callback, ResponsibleEmployeeCB(employee_id=7), state
        )

        assert "&lt;b&gt;Bold Bat" in callback.message.edit_text.await_args.args[0]
        assert (await load_defect(state)).responsible_employee_label == "<b>Bold Bat"

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
