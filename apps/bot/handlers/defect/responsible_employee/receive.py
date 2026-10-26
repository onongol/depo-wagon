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
from apps.bot.constants import FSMKey
from apps.bot.fsm import drop_keys, load_defect, save_defect
from apps.bot.handlers.defect.scene import STEP_TEXT, DefectScene
from apps.bot.states import DefectSG
from apps.bot.utils.screens import delete_input, show_screen

from .list import employee_list_screen

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery, Message

    from apps.bot.handlers.defect.scene import Screen
    from apps.bot.user_data import DefectData


class ResponsibleEmployeeScene(DefectScene, state=DefectSG.responsible_employee.state):
    """Human factor only: someone from the form's department, paged or searched by name."""

    async def _record(
        self, state: FSMContext, employee_id: int | None, label: str | None
    ) -> None:
        defect = await load_defect(state)
        defect.responsible_employee_id = employee_id
        defect.responsible_employee_label = label
        await save_defect(state, defect)
        await drop_keys(state, FSMKey.RESP_SEARCH)
        await self.go_on(state, DefectSG.photo)

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.defect_type

    @classmethod
    async def screen(
        cls, form: DefectData, data: dict[str, Any], page: int = 0
    ) -> Screen:
        search = data.get(FSMKey.RESP_SEARCH, "")
        return await employee_list_screen(form.department, search, page)

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
        await self._record(state, employee.id, label)

    @on.callback_query(F.data == CB_RESP_EMP_SKIP)
    async def skip(self, callback: CallbackQuery, state: FSMContext) -> None:
        """No one, which also clears someone Edit ▸ Responsible reopened."""
        await callback.answer()
        await self._record(state, None, None)

    @on.callback_query(ResponsibleEmployeePageCB.filter())
    async def turn_page(
        self,
        callback: CallbackQuery,
        callback_data: ResponsibleEmployeePageCB,
        state: FSMContext,
    ) -> None:
        await callback.answer()

        content, keyboard = await self.draw(
            await load_defect(state), await state.get_data(), page=callback_data.page
        )
        await show_screen(
            callback.bot,
            state,
            callback.from_user.id,
            tapped=callback.message,
            reply_markup=keyboard,
            **content.as_kwargs(),
        )

    @on.message(*STEP_TEXT)
    async def search(self, message: Message, state: FSMContext) -> None:
        """A typed name narrows the list, drawn anew from its first page."""
        await delete_input(message)
        await state.update_data({FSMKey.RESP_SEARCH: message.text.strip()})
        await self.wizard.retake()

    @on.callback_query(F.data == CB_RESP_EMP_ALL)
    async def show_all(self, callback: CallbackQuery, state: FSMContext) -> None:
        """Drops the search: the whole department again, from its first page."""
        await callback.answer()
        await drop_keys(state, FSMKey.RESP_SEARCH)
        await self.wizard.retake()
