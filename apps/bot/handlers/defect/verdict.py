import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import VERDICT_LABELS
from apps.bot.keyboards import main_menu_keyboard
from apps.bot.messages import BotMessages as M

logger = logging.getLogger(__name__)


async def _notify_decommission(
    context: ContextTypes.DEFAULT_TYPE,
    employee,
    defect_data: dict,
) -> None:
    """Send decommission alert to all managers and engineers."""
    managers = await services.get_managers_and_engineers()
    if not managers:
        return

    text = str(M.DECOMMISSION_ALERT).format(
        wagon_number=defect_data.get("wagon_number", "?"),
        node_label=defect_data.get("node_label", "?"),
        defect_type_label=defect_data.get("defect_type_label", "?"),
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

    verdict_value = query.data.split(":", 1)[1]
    defect_data = context.user_data.get("defect", {})
    defect_id = defect_data.get("defect_id")
    employee = context.user_data.get("employee")

    if defect_id:
        await services.save_employee_verdict(defect_id, verdict_value)

    if verdict_value == "decommission":
        await _notify_decommission(context, employee, defect_data)

    verdict_label = str(VERDICT_LABELS.get(verdict_value, verdict_value))

    # Remove inline keyboard from the verdict prompt message
    await query.edit_message_reply_markup(reply_markup=None)

    # Send final confirmation with main menu
    await query.message.reply_text(
        str(M.VERDICT_DONE).format(label=verdict_label),
        parse_mode=M.PARSE_MODE,
        reply_markup=main_menu_keyboard(employee.role) if employee else None,
    )

    context.user_data.pop("defect", None)
    return ConversationHandler.END
