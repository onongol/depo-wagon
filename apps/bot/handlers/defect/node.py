from typing import TYPE_CHECKING

from apps.bot.callback_data import CB_PART_NUMBER_SKIP
from apps.bot.constants import UD_EDITING
from apps.bot.fsm import load_defect, save_defect
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.defects.constants import DefectNode

from .summary import show_summary

if TYPE_CHECKING:
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import NodeCB

_NODE_LABELS = dict(DefectNode.choices)


async def receive_node(
    callback: CallbackQuery, callback_data: NodeCB, state: FSMContext
) -> None:
    """Handle incoming node selection from inline keyboard."""
    await callback.answer()

    node_value = callback_data.value
    node_label = _NODE_LABELS.get(node_value, node_value)

    defect = await load_defect(state)
    defect.node = node_value
    defect.node_label = node_label
    await save_defect(state, defect)

    if (await state.get_data()).get(UD_EDITING):
        await show_summary(callback.message.edit_text, state, defect)
        return

    await callback.message.edit_text(
        str(M.NODE_CONFIRMED).format(label=node_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=skip_keyboard(CB_PART_NUMBER_SKIP),
    )
    await state.set_state(DefectSG.part_number)
