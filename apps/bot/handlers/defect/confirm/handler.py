import logging
from typing import TYPE_CHECKING

from apps.bot.constants import UD_DEFECT, UD_SCREEN
from apps.bot.fsm import drop_keys, load_defect, save_defect
from apps.bot.handlers.defect.notifications import notify_decommission
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.utils.screens import answer_anew
from apps.defects.constants import DefectVerdict

from .formatters import build_recommendation_text, build_result_text
from .pipeline import register_defect, run_ai_analysis

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from aiogram.types import CallbackQuery

    from apps.core.models import Employee

logger = logging.getLogger(__name__)


async def confirm_defect(
    callback: CallbackQuery, state: FSMContext, bot: Bot, employee: Employee | None
) -> None:
    """Drive the save pipeline, switch progress messages, and show the result."""
    await callback.answer()

    defect_data = await load_defect(state)
    if not employee:
        await callback.message.edit_text(str(M.NOT_REGISTERED))
        await state.set_state(None)
        return

    # The screen becomes the result, so nothing may take it down after this
    await drop_keys(state, UD_SCREEN)

    # Critical: a failure here means nothing was saved
    await callback.message.edit_text(str(M.SAVING))
    # Out of confirm before the save, so a queued second tap cannot save twice.
    await state.set_state(DefectSG.saving)
    try:
        registered = await register_defect(defect_data, employee, bot)
    except Exception:
        logger.exception("Failed to save defect")
        await answer_anew(
            callback,
            text=str(M.SAVE_FAILED),
            parse_mode=M.PARSE_MODE,
            reply_markup=main_menu_keyboard(),
        )
        await state.set_state(None)
        return

    defect_data.defect_id = str(registered.defect.id)
    await save_defect(state, defect_data)

    if defect_data.verdict == DefectVerdict.DECOMMISSION:
        try:
            await notify_decommission(bot, employee, defect_data)
        except Exception:
            logger.exception("Decommission alert failed for %s", defect_data.defect_id)

    # Non-critical: an AI failure must not undo the save above
    await callback.message.edit_text(str(M.AI_ANALYZING))
    ai_result = await run_ai_analysis(
        defect_data, registered.defect.id, registered.photo_bytes
    )

    await callback.message.edit_text(
        build_result_text(registered.defect.id, defect_data.verdict, ai_result),
        parse_mode=M.PARSE_MODE,
    )

    recommendation = build_recommendation_text(ai_result)
    if recommendation:
        await callback.message.answer(recommendation, parse_mode=M.PARSE_MODE)

    await callback.message.answer(
        str(M.REGISTRATION_DONE), reply_markup=main_menu_keyboard()
    )
    await drop_keys(state, UD_DEFECT)
    await state.set_state(None)
