from typing import TYPE_CHECKING, Any

from aiogram import F
from aiogram.fsm.scene import on

from apps.bot import services
from apps.bot.callback_data import (
    CB_RESP_EMP_ALL,
    CB_RESP_EMP_SKIP,
    ResponsibleEmployeeCB,
    ResponsibleEmployeePageCB,
)
from apps.bot.constants import UD_RESP_SEARCH
from apps.bot.fsm import drop_keys, load_defect, save_defect
from apps.bot.handlers.defect.scene import STEP_TEXT, DefectScene, as_send_kwargs
from apps.bot.states import DefectSG
from apps.bot.utils.screens import edit_or_send

from .list import employee_list_screen

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery, Message

    from apps.bot.handlers.defect.scene import Screen
    from apps.bot.user_data import DefectData


class ResponsibleEmployeeScene(DefectScene, state=DefectSG.responsible_employee.state):
    """Human factor only: someone from the form's department, paged or searched by name."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        return await employee_list_screen(form.department, data.get(UD_RESP_SEARCH, ""))

    @on.callback_query(ResponsibleEmployeeCB.filter())
    async def select(
        self,
        callback: CallbackQuery,
        callback_data: ResponsibleEmployeeCB,
        state: FSMContext,
    ) -> None:
        """Someone deactivated or moved out since the page was drawn gets the list again."""
        await callback.answer()

        defect = await load_defect(state)
        employee = await services.get_department_employee(
            callback_data.employee_id, defect.department
        )
        if employee is None:
            await self.wizard.retake()
            return

        label = f"{employee.first_name} {employee.last_name}"
        defect.responsible_employee_id = employee.id
        defect.responsible_employee_label = label
        await save_defect(state, defect)
        await drop_keys(state, UD_RESP_SEARCH)

        await self.go_on(state, DefectSG.severity)

    @on.callback_query(F.data == CB_RESP_EMP_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        await callback.answer()

        defect = await load_defect(state)
        defect.responsible_employee_id = None
        defect.responsible_employee_label = None
        await save_defect(state, defect)
        await drop_keys(state, UD_RESP_SEARCH)

        await self.go_on(state, DefectSG.severity)

    @on.callback_query(ResponsibleEmployeePageCB.filter())
    async def turn_page(
        self,
        callback: CallbackQuery,
        callback_data: ResponsibleEmployeePageCB,
        state: FSMContext,
    ) -> None:
        await callback.answer()

        defect = await load_defect(state)
        search = (await state.get_data()).get(UD_RESP_SEARCH, "")
        content, keyboard = await employee_list_screen(
            defect.department, search, callback_data.page
        )
        await edit_or_send(callback, **as_send_kwargs(content), reply_markup=keyboard)

    @on.message(*STEP_TEXT)
    async def search(self, message: Message, state: FSMContext) -> None:
        """A typed name narrows the list, drawn anew from its first page."""
        await state.update_data({UD_RESP_SEARCH: message.text.strip()})
        await self.wizard.retake()

    @on.callback_query(F.data == CB_RESP_EMP_ALL)
    async def show_all(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Drops the search: the whole department again, from its first page."""
        await callback.answer()
        await drop_keys(state, UD_RESP_SEARCH)
        await self.wizard.retake()
