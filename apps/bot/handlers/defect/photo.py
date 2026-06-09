import logging

from telegram import Update
from telegram.ext import ContextTypes

from apps.bot import services
from apps.bot.callbacks import PhotoSkipCB
from apps.bot.constants import UD_DEFECT
from apps.bot.keyboards.common import skip_keyboard
from apps.bot.keyboards.defect import measurement_choice_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import MEASUREMENT_CHOICE, PHOTO, RESPONSIBLE_EMPLOYEE
from apps.bot.user_data import DefectData
from apps.defects.validators import MAX_PHOTO_BYTES

logger = logging.getLogger(__name__)

PHOTO_MG = "photo_mg_"
UD_LAST_PHOTO_MSG = "_last_photo_msg"


async def _clear_last_photo_keyboard(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the inline keyboard from the previous photo-count message."""
    prev_msg = context.user_data.pop(UD_LAST_PHOTO_MSG, None)
    if prev_msg:
        try:
            await prev_msg.edit_reply_markup(reply_markup=None)
        except Exception:
            pass


async def _after_photos(query_or_msg, defect: DefectData, context, edit: bool) -> int:
    """Route to responsible_employee or measurement depending on defect type."""
    context.user_data.pop(UD_LAST_PHOTO_MSG, None)

    from apps.defects.constants import DefectType

    if defect.defect_type == DefectType.HUMAN_FACTOR:
        from apps.bot.handlers.defect.responsible_employee import (
            UD_RESP_EMPLOYEES,
            UD_RESP_SEARCH,
            show_responsible_employee_list,
        )

        employees = await services.get_employees_by_department(defect.department or "")
        context.user_data[UD_RESP_EMPLOYEES] = employees
        context.user_data[UD_RESP_SEARCH] = ""
        await show_responsible_employee_list(query_or_msg, context, page=0, edit=edit)
        return RESPONSIBLE_EMPLOYEE

    text = str(M.ASK_MEASUREMENT)
    if edit:
        await query_or_msg.edit_message_text(
            text, reply_markup=measurement_choice_keyboard()
        )
    else:
        await query_or_msg.reply_text(text, reply_markup=measurement_choice_keyboard())
    return MEASUREMENT_CHOICE


async def _flush_media_group(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send batched photo count after all album photos are collected."""
    user_id = context.job.user_id
    chat_id = context.job.chat_id
    user_data = context.application.user_data.get(user_id, {})
    defect: DefectData | None = user_data.get(UD_DEFECT)
    count = len(defect.photo_file_ids) if defect else 0

    # Remove keyboard from previous photo message
    prev_msg = user_data.pop(UD_LAST_PHOTO_MSG, None)
    if prev_msg:
        try:
            await prev_msg.edit_reply_markup(reply_markup=None)
        except Exception:
            pass

    msg = await context.bot.send_message(
        chat_id=chat_id,
        text=str(M.PHOTO_RECEIVED).format(count=count),
        reply_markup=skip_keyboard(PhotoSkipCB()),
    )
    user_data[UD_LAST_PHOTO_MSG] = msg


async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle incoming photo or skip action."""
    if update.callback_query:
        await update.callback_query.answer()
        defect_skip: DefectData = context.user_data[UD_DEFECT]
        return await _after_photos(
            update.callback_query, defect_skip, context, edit=True
        )

    photo = update.message.photo[-1]

    if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
        await update.message.reply_text(str(M.PHOTO_TOO_LARGE))
        return PHOTO

    defect: DefectData = context.user_data[UD_DEFECT]
    defect.photo_file_ids.append(photo.file_id)

    if update.message.media_group_id and context.job_queue is not None:
        job_name = f"{PHOTO_MG}{update.effective_user.id}"
        for job in context.job_queue.get_jobs_by_name(job_name):
            job.schedule_removal()
        context.job_queue.run_once(
            _flush_media_group,
            when=0.5,
            name=job_name,
            user_id=update.effective_user.id,
            chat_id=update.effective_chat.id,
        )
    else:
        await _clear_last_photo_keyboard(context)
        msg = await update.message.reply_text(
            str(M.PHOTO_RECEIVED).format(count=len(defect.photo_file_ids)),
            reply_markup=skip_keyboard(PhotoSkipCB()),
        )
        context.user_data[UD_LAST_PHOTO_MSG] = msg

    return PHOTO
