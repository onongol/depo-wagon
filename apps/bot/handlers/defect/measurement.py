import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot.keyboards import (
    dimension_keyboard,
    measurement_choice_keyboard,
    measurement_next_keyboard,
    skip_keyboard,
)
from apps.bot.messages import BotMessages as M
from apps.bot.states import (
    DESC,
    MEASUREMENT_CHOICE,
    MEASUREMENT_DIMENSION,
    MEASUREMENT_NORM,
    MEASUREMENT_UNIT,
    MEASUREMENT_VALUE,
)

logger = logging.getLogger(__name__)


async def ask_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for measurement sub-flow."""
    query = update.callback_query
    await query.answer()

    context.user_data["defect"].setdefault("measurements", [])

    await query.edit_message_text(
        str(M.ASK_MEASUREMENT),
        reply_markup=measurement_choice_keyboard(),
    )
    return MEASUREMENT_CHOICE


async def handle_measurement_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handle user's choice to add measurement or skip."""
    query = update.callback_query
    await query.answer()

    action = query.data.split(":", 1)[1]  # "add" | "skip" | "done"

    if action in ("skip", "done"):
        await query.edit_message_text(
            str(M.ASK_DESCRIPTION),
            reply_markup=skip_keyboard("desc:skip"),
        )
        return DESC

    # action == "add" → ask for dimension
    context.user_data["defect"]["current_measurement"] = {}
    await query.edit_message_text(
        str(M.ASK_DIMENSION),
        reply_markup=dimension_keyboard(),
    )
    return MEASUREMENT_DIMENSION


async def receive_dimension(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive selected dimension from inline keyboard."""
    query = update.callback_query
    await query.answer()

    dim_value = query.data.split(":", 1)[1]

    from apps.defects.constants import MeasurementDimension

    dim_label = dict(MeasurementDimension.choices).get(dim_value, dim_value)

    context.user_data["defect"]["current_measurement"]["dimension"] = dim_value
    context.user_data["defect"]["current_measurement"]["dimension_label"] = dim_label

    await query.edit_message_text(
        str(M.DIMENSION_CONFIRMED).format(label=dim_label),
        parse_mode=M.PARSE_MODE,
    )
    return MEASUREMENT_VALUE


async def receive_measurement_value(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Receive measurement value as text, validate and save."""
    text = update.message.text.strip()

    try:
        value = float(text.replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            str(M.VALUE_INVALID),
            parse_mode=M.PARSE_MODE,
        )
        return MEASUREMENT_VALUE

    context.user_data["defect"]["current_measurement"]["value"] = value

    await update.message.reply_text(
        str(M.ASK_NORM),
        reply_markup=skip_keyboard("norm:skip"),
    )
    return MEASUREMENT_NORM


async def receive_norm_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Norm value is optional, so user can skip by button or enter text."""
    if update.callback_query:
        await update.callback_query.answer()
        context.user_data["defect"]["current_measurement"]["norm_value"] = None
        await update.callback_query.edit_message_text(
            str(M.ASK_UNIT),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard("unit:skip"),
        )
    else:
        text = update.message.text.strip()
        try:
            norm = float(text.replace(",", "."))
        except ValueError:
            await update.message.reply_text(
                str(M.NORM_INVALID),
                parse_mode=M.PARSE_MODE,
                reply_markup=skip_keyboard("norm:skip"),
            )
            return MEASUREMENT_NORM
        context.user_data["defect"]["current_measurement"]["norm_value"] = norm
        await update.message.reply_text(
            str(M.ASK_UNIT),
            parse_mode=M.PARSE_MODE,
            reply_markup=skip_keyboard("unit:skip"),
        )
    return MEASUREMENT_UNIT


async def receive_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Unit is optional, so user can skip by button or enter text."""
    current = context.user_data["defect"]["current_measurement"]

    if update.callback_query:
        await update.callback_query.answer()
        current["unit"] = ""
        send = update.callback_query.edit_message_text
    else:
        current["unit"] = update.message.text.strip()
        send = update.message.reply_text

    # Save completed measurement to list
    context.user_data["defect"]["measurements"].append(
        {
            "dimension": current.get("dimension", ""),
            "dimension_label": current.get("dimension_label", ""),
            "value": current.get("value"),
            "norm_value": current.get("norm_value"),
            "unit": current.get("unit", ""),
        }
    )
    context.user_data["defect"].pop("current_measurement", None)

    count = len(context.user_data["defect"]["measurements"])
    dim_label = current.get("dimension_label", "")
    value = current.get("value")
    unit = f" {current['unit']}" if current.get("unit") else ""

    await send(
        str(M.MEASUREMENT_SAVED).format(
            count=count,
            label=dim_label,
            value=value,
            unit=unit,
        ),
        parse_mode=M.PARSE_MODE,
        reply_markup=measurement_next_keyboard(),
    )
    return MEASUREMENT_CHOICE
