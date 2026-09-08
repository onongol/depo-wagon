import logging
from typing import TYPE_CHECKING

from apps.bot.fsm import clear_defect_keys, load_defect, save_defect
from apps.bot.handlers.employee import get_employee
from apps.bot.keyboards.defect import employee_verdict_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG

from .formatters import build_recommendation_text, build_result_text
from .pipeline import register_defect, run_ai_analysis

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.bot.callback_data import ConfirmCB

logger = logging.getLogger(__name__)


async def confirm_defect(
    callback: CallbackQuery, callback_data: ConfirmCB, state: FSMContext, bot: Bot
) -> None:
    """Drive the save pipeline, switch progress messages, and show the result."""
    await callback.answer()

    if not callback_data.confirmed:
        await clear_defect_keys(state)
        await state.set_state(None)
        await callback.message.edit_text(str(M.DEFECT_CANCELLED))
        return

    defect_data = await load_defect(state)
    employee = await get_employee(callback.from_user.id)
    if not employee:
        await callback.message.edit_text(str(M.NOT_REGISTERED))
        await state.set_state(None)
        return

    # Critical: a failure here means nothing was saved
    await callback.message.edit_text(str(M.SAVING))
    try:
        registered = await register_defect(defect_data, employee, bot)
    except Exception:
        logger.exception("Failed to save defect")
        await callback.message.edit_text(str(M.SAVE_FAILED), parse_mode=M.PARSE_MODE)
        await state.set_state(None)
        return

    defect_data.defect_id = str(registered.defect.id)
    await save_defect(state, defect_data)

    # Non-critical: an AI failure must not undo the save above
    await callback.message.edit_text(str(M.AI_ANALYZING))
    ai_result = await run_ai_analysis(
        defect_data, registered.defect.id, registered.photo_bytes
    )

    await callback.message.edit_text(
        build_result_text(registered.defect.id, ai_result), parse_mode=M.PARSE_MODE
    )

    recommendation = build_recommendation_text(ai_result)
    if recommendation:
        await callback.message.answer(recommendation, parse_mode=M.PARSE_MODE)

    await callback.message.answer(
        str(M.ASK_EMPLOYEE_VERDICT),
        parse_mode=M.PARSE_MODE,
        reply_markup=employee_verdict_keyboard(),
    )
    await state.set_state(DefectSG.employee_verdict)
