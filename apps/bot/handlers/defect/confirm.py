import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.bot import services
from apps.bot.constants import UD_DEFECT, UD_EMPLOYEE, VERDICT_TEXT
from apps.bot.user_data import DefectData
from apps.bot.keyboards.defect import employee_verdict_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import EMPLOYEE_VERDICT

logger = logging.getLogger(__name__)


async def confirm_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if not query.data.confirmed:
        context.user_data.pop(UD_DEFECT, None)
        await query.edit_message_text(str(M.DEFECT_CANCELLED))
        return ConversationHandler.END

    await query.edit_message_text(str(M.SAVING))

    defect_data: DefectData = context.user_data[UD_DEFECT]
    employee = context.user_data.get(UD_EMPLOYEE)

    try:
        # 1. Create Defect record
        saved_defect = await services.create_defect(
            wagon_id=defect_data.wagon_id,
            node=defect_data.node,
            defect_type=defect_data.defect_type,
            severity=defect_data.severity,
            description=defect_data.description,
            employee_id=employee.id if employee else None,
        )

        # 2. Save measurements
        for measurement in defect_data.measurements:
            try:
                await services.create_measurement(
                    defect_id=saved_defect.id,
                    dimension=measurement.dimension,
                    value=measurement.value,
                    norm_value=measurement.norm_value,
                    unit=measurement.unit,
                )
            except Exception as exc:
                logger.warning("Measurement save failed: %s", exc)

        # 3. Download and save all photos
        all_photo_bytes: list[bytes] = []

        for idx, file_id in enumerate(defect_data.photo_file_ids):
            try:
                file = await context.bot.get_file(file_id)
                file_bytes = bytes(await file.download_as_bytearray())
                filename = f"bot_{saved_defect.id}_{idx + 1}_{file_id[-8:]}.jpg"

                await services.create_photo_from_bytes(
                    defect_id=saved_defect.id,
                    file_bytes=file_bytes,
                    filename=filename,
                )

                all_photo_bytes.append(file_bytes)
            except Exception as exc:
                logger.warning("Photo save failed (idx=%d): %s", idx, exc)

        # 4. AI analysis — all photos + description
        await query.edit_message_text(str(M.AI_ANALYZING))

        from apps.bot.ai_analysis import analyze_defect

        ai_result = await analyze_defect(
            node=defect_data.node_label or "",
            defect_type=defect_data.defect_type_label or "",
            severity=defect_data.severity_label or "",
            description=defect_data.description,
            photos_bytes=all_photo_bytes or None,
        )

        if ai_result.defect_class:
            await services.update_defect_ai_result(
                defect_id=saved_defect.id,
                ai_class=ai_result.defect_class,
                ai_confidence=ai_result.confidence,
                ai_recommendation=ai_result.recommendation,
                ai_verdict=ai_result.verdict,
            )

        # 5. Build result message
        result_text = str(M.SAVE_SUCCESS).format(short_id=str(saved_defect.id)[:8])

        if ai_result.defect_class:
            confidence_pct = int((ai_result.confidence or 0) * 100)
            verdict_tuple = VERDICT_TEXT.get(ai_result.verdict)
            verdict_emoji = verdict_tuple[0] if verdict_tuple else "ℹ️"
            verdict_label = str(verdict_tuple[1]) if verdict_tuple else "—"
            result_text += str(M.AI_RESULT).format(
                defect_class=html.escape(ai_result.defect_class),
                confidence=confidence_pct,
                verdict_emoji=verdict_emoji,
                verdict=verdict_label,
                recommendation=html.escape(ai_result.recommendation),
            )
        else:
            result_text += str(M.AI_UNAVAILABLE)

        defect_data.defect_id = str(saved_defect.id)

        # Message 1: save result + AI analysis (no keyboard)
        await query.edit_message_text(result_text, parse_mode=M.PARSE_MODE)

        # Message 2: verdict keyboard as a separate message
        await query.message.reply_text(
            str(M.ASK_EMPLOYEE_VERDICT),
            parse_mode=M.PARSE_MODE,
            reply_markup=employee_verdict_keyboard(),
        )
        return EMPLOYEE_VERDICT

    except Exception as exc:
        logger.error("Failed to save defect: %s", exc, exc_info=True)
        await query.edit_message_text(
            str(M.SAVE_FAILED).format(error=html.escape(str(exc))),
            parse_mode=M.PARSE_MODE,
        )
        return ConversationHandler.END
