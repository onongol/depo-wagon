from typing import TYPE_CHECKING, Any

from aiogram.fsm.scene import on

from apps.bot.callback_data import CB_PART_NUMBER_SKIP, NodeCB
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import node_keyboard_for_department
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectNode

from .scene import DefectScene
from .text import build_department_confirmed_text

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.user_data import DefectData

    from .scene import Screen

_NODE_LABELS = dict(DefectNode.choices)


class NodeScene(DefectScene, state=DefectSG.node.state):
    """The node, from the buttons for the department picked; Edit ▸ Node reopens it."""

    @classmethod
    async def screen(cls, form: DefectData, data: dict[str, Any]) -> Screen:
        keyboard = node_keyboard_for_department(form.department or "")
        if data.get(UD_EDITING):
            return str(M.EDIT_NODE), keyboard
        return build_department_confirmed_text(form.department_label), keyboard

    @on.callback_query(NodeCB.filter())
    async def receive(
        self, callback: CallbackQuery, callback_data: NodeCB, state: FSMContext
    ) -> None:
        await callback.answer()

        node_value = callback_data.value
        node_label = str(_NODE_LABELS.get(node_value, node_value))

        defect = await load_defect(state)
        defect.node = node_value
        defect.node_label = node_label
        await save_defect(state, defect)

        if await self.back_to_summary_if_editing(state):
            return

        await callback.message.edit_text(
            str(M.NODE_CONFIRMED).format(label=node_label),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard(CB_PART_NUMBER_SKIP),
        )
        await state.set_state(DefectSG.part_number)
