import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import UD_DEFECT, UD_EMPLOYEE, VERDICT_LABELS
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.user_data import DefectData
from apps.defects.constants import DefectVerdict

from .notifications import notify_decommission

logger = logging.getLogger(__name__)


async def receive_employee_verdict(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle incoming verdict selection from inline keyboard."""
    query = update.callback_query
    await query.answer()

    verdict_value = query.data.value

    defect: DefectData = context.user_data.get(UD_DEFECT)
    employee = context.user_data.get(UD_EMPLOYEE)

    if defect and defect.defect_id:
        try:
            await services.save_employee_verdict(defect.defect_id, verdict_value)
        except Exception:
            logger.exception("Failed to save verdict for defect %s", defect.defect_id)
            await query.edit_message_text(str(M.SESSION_ERROR))
            return ConversationHandler.END

        if verdict_value == DefectVerdict.DECOMMISSION:
            await notify_decommission(context, employee, defect)

    verdict_label = str(VERDICT_LABELS.get(verdict_value, verdict_value))

    # Prevent re-clicking verdict buttons after conversation ends (stale callback)
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        logger.debug("Could not clear verdict keyboard (message deleted or too old)")

    await query.message.reply_text(
        str(M.VERDICT_DONE).format(label=verdict_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(employee.role) if employee else None,
    )

    context.user_data.pop(UD_DEFECT, None)
    return ConversationHandler.END
