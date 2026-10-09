from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import NodeCB
from apps.bot.constants import FSMKey
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.defect import node_keyboard_for_department
from apps.bot.states import DefectSG

from .scene import DefectScene
from .text import build_ask_node_text, build_edit_node_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.fsm.state import State
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen


class NodeScene(DefectScene, state=DefectSG.node.state):
    """The node, from the buttons for the department picked; Edit ▸ Node reopens it."""

    @classmethod
    def previous(cls, form: DefectData) -> State | None:
        return DefectSG.department

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        keyboard = node_keyboard_for_department(form.department or "")
        if data.get(FSMKey.EDITING):
            return build_edit_node_text(), keyboard
        return build_ask_node_text(), keyboard

    @on.callback_query(NodeCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: NodeCB, state: FSMContext
    ) -> None:
        await callback.answer()

        defect = await load_defect(state)
        defect.node = callback_data.value
        await save_defect(state, defect)

        await self.go_on(state, DefectSG.part_number)
