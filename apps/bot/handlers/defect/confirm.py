import asyncio
import html
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from apps.ai_service.analysis import analyze_defect
from apps.bot import services
from apps.bot.constants import UD_DEFECT, UD_EMPLOYEE, VERDICT_TEXT
from apps.bot.handlers.defect.cancel import _DEFECT_KEYS
from apps.bot.keyboards.defect import employee_verdict_keyboard
from apps.bot.messages import BotMessages as M
from apps.bot.states import EMPLOYEE_VERDICT
from apps.bot.user_data import DefectData
from apps.defects.validators import MAX_PHOTO_BYTES

logger = logging.getLogger(__name__)


async def confirm_defect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle defect confirmation, save to DB, run AI analysis, and show results."""
    query = update.callback_query
    await query.answer()

    if not query.data.confirmed:
        for key in _DEFECT_KEYS:
            context.user_data.pop(key, None)
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
            department=defect_data.department or "",
            part_number=defect_data.part_number or "",
            responsible_employee_id=defect_data.responsible_employee_id,
        )

        # 2. Download and save all photos in parallel
        async def _fetch_and_save_photo(idx: int, file_id: str) -> bytes | None:
            try:
                file = await context.bot.get_file(file_id)
                if file.file_size and file.file_size > MAX_PHOTO_BYTES:
                    logger.warning(
                        "Photo too large (%d bytes), skipping", file.file_size
                    )
                    return None
                file_bytes = bytes(await file.download_as_bytearray())
                filename = f"bot_{saved_defect.id}_{idx + 1}_{file_id[-8:]}.jpg"
                await services.create_photo_from_bytes(
                    defect_id=saved_defect.id,
                    file_bytes=file_bytes,
                    filename=filename,
                )
                return file_bytes
            except Exception as exc:
                logger.warning("Photo save failed (idx=%d): %s", idx, exc)
                return None

        results = await asyncio.gather(
            *[
                _fetch_and_save_photo(i, fid)
                for i, fid in enumerate(defect_data.photo_file_ids)
            ]
        )
        all_photo_bytes: list[bytes] = [b for b in results if b is not None]

        # 3. Save measurements
        if defect_data.measurements:
            try:
                await services.create_measurements_bulk(
                    saved_defect.id, defect_data.measurements
                )
            except Exception as exc:
                logger.warning("Measurements save failed: %s", exc)

        # 4. AI analysis — all photos + description
        await query.edit_message_text(str(M.AI_ANALYZING))

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
                ai_recommendation=ai_result.rag_recommendation,
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
            )
        else:
            result_text += str(M.AI_UNAVAILABLE)

        defect_data.defect_id = str(saved_defect.id)

        # Message 1: save result + structured AI analysis
        await query.edit_message_text(result_text, parse_mode=M.PARSE_MODE)

        # Message 2: RAG recommendation as a separate message
        if ai_result.rag_recommendation:
            await query.message.reply_text(
                str(M.AI_RECOMMENDATION).format(
                    rag_recommendation=html.escape(ai_result.rag_recommendation),
                ),
                parse_mode=M.PARSE_MODE,
            )

        # Message 3: verdict keyboard
        await query.message.reply_text(
            str(M.ASK_EMPLOYEE_VERDICT),
            parse_mode=M.PARSE_MODE,
            reply_markup=employee_verdict_keyboard(),
        )
        return EMPLOYEE_VERDICT

    except Exception:
        logger.exception("Failed to save defect")
        await query.edit_message_text(str(M.SAVE_FAILED), parse_mode=M.PARSE_MODE)
        return ConversationHandler.END
