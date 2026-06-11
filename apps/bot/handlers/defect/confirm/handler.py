import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot.constants import DEFECT_USER_DATA_KEYS, UD_DEFECT, UD_EMPLOYEE
from apps.bot.keyboards.defect import employee_verdict_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import EMPLOYEE_VERDICT
from apps.bot.user_data import DefectData

from .formatters import build_recommendation_text, build_result_text
from .pipeline import register_defect, run_ai_analysis

logger = logging.getLogger(__name__)


async def confirm_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Drive the save pipeline, switch progress messages, and show the result."""
    query = update.callback_query
    await query.answer()

    if not query.data.confirmed:
        for key in DEFECT_USER_DATA_KEYS:
            context.user_data.pop(key, None)
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    defect_data: DefectData = context.user_data.get(UD_DEFECT)
    employee = context.user_data.get(UD_EMPLOYEE)

    # Critical: a failure here means nothing was saved
    await query.edit_message_text(str(M.SAVING))
    try:
        registered = await register_defect(defect_data, employee, context.bot)
    except Exception:
        logger.exception("Failed to save defect")
        await query.edit_message_text(str(M.SAVE_FAILED), parse_mode=M.PARSE_MODE)
        return ConversationHandler.END

    defect_data.defect_id = str(registered.defect.id)

    # Non-critical: an AI failure must not undo the save above
    await query.edit_message_text(str(M.AI_ANALYZING))
    ai_result = await run_ai_analysis(
        defect_data, registered.defect.id, registered.photo_bytes
    )

    await query.edit_message_text(
        build_result_text(registered.defect, ai_result), parse_mode=M.PARSE_MODE
    )

    recommendation = build_recommendation_text(ai_result)
    if recommendation:
        await query.message.reply_text(recommendation, parse_mode=M.PARSE_MODE)

    await query.message.reply_text(
        str(M.ASK_EMPLOYEE_VERDICT),
        parse_mode=M.PARSE_MODE,
        reply_markup=employee_verdict_keyboard(),
    )
    return EMPLOYEE_VERDICT
