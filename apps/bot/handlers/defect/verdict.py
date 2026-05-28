import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import UD_DEFECT, UD_EMPLOYEE, VERDICT_LABELS
from apps.bot.user_data import DefectData
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.messages import BotMessages as M
from apps.defects.constants import DefectVerdict

logger = logging.getLogger(__name__)


async def _notify_decommission(
    context: ContextTypes.DEFAULT_TYPE,
    employee,
    defect: DefectData | None,
) -> None:
    """Send decommission alert to all managers and engineers."""
    managers = await services.get_managers_and_engineers()
    if not managers:
        return

    text = str(M.DECOMMISSION_ALERT).format(
        wagon_number=defect.wagon_number if defect else "?",
        node_label=defect.node_label if defect else "?",
        defect_type_label=defect.defect_type_label if defect else "?",
        inspector_name=employee.full_name if employee else "—",
    )

    for manager in managers:
        try:
            await context.bot.send_message(
                chat_id=manager.telegram_id,
                text=text,
                parse_mode=M.PARSE_MODE,
            )
        except Exception as exc:
            logger.warning(
                "Failed to notify manager %s (tg=%s): %s",
                manager.full_name,
                manager.telegram_id,
                exc,
            )


async def receive_employee_verdict(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()

    verdict_value = query.data.value
    
    defect: DefectData = context.user_data.get(UD_DEFECT)
    employee = context.user_data.get(UD_EMPLOYEE)

    if defect and defect.defect_id:
        await services.save_employee_verdict(defect.defect_id, verdict_value)

    if verdict_value == DefectVerdict.DECOMMISSION:
        await _notify_decommission(context, employee, defect)

    verdict_label = str(VERDICT_LABELS.get(verdict_value, verdict_value))

    # Remove inline keyboard from the verdict prompt message
    await query.edit_message_reply_markup(reply_markup=None)

    # Send final confirmation with main menu
    await query.message.reply_text(
        str(M.VERDICT_DONE).format(label=verdict_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(employee.role) if employee else None,
    )

    context.user_data.pop(UD_DEFECT, None)
    return ConversationHandler.END
