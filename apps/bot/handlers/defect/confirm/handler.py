import logging
from typing import TYPE_CHECKING

from apps.bot.constants import UD_DEFECT, UD_SCREEN
from apps.bot.fsm import drop_keys, load_defect, save_defect
from apps.bot.handlers.defect.notifications import notify_decommission
from apps.bot.handlers.defect.text import (
    build_ai_analyzing_text,
    build_recommendation_text,
    build_result_text,
    build_save_failed_text,
    build_saving_text,
)
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import DefectSG
from apps.bot.utils.screens import answer_anew, take_down
from apps.defects.constants import DefectVerdict

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

    await drop_keys(state, UD_SCREEN)
    await callback.message.edit_text(**build_saving_text().as_kwargs())
    await state.set_state(DefectSG.saving)

    try:
        registered = await register_defect(defect_data, employee, bot)
    except Exception:
        logger.exception("Failed to save defect")
        await answer_anew(
            callback,
            **build_save_failed_text().as_kwargs(),
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

    await callback.message.edit_text(**build_ai_analyzing_text().as_kwargs())
    ai_result = await run_ai_analysis(
        defect_data, registered.defect.id, registered.photo_bytes
    )

    # Sent anew: only a new message can bring the menu back
    result = build_result_text(registered.defect.id, defect_data.verdict, ai_result)
    await callback.message.answer(
        **result.as_kwargs(), reply_markup=main_menu_keyboard()
    )
    await take_down(bot, [callback.message.chat.id, callback.message.message_id])

    recommendation = build_recommendation_text(ai_result)
    if recommendation:
        await callback.message.answer(**recommendation.as_kwargs())

    await drop_keys(state, UD_DEFECT)
    await state.set_state(None)
