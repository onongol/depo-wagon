import html

from apps.bot.constants import VERDICT_TEXT
from apps.bot.messages import BotMessages as M


def build_result_text(defect_id, ai_result) -> str:
    """Build the save-confirmation message with structured AI analysis."""
    result_text = str(M.SAVE_SUCCESS).format(short_id=str(defect_id)[:8])

    if ai_result and ai_result.defect_class:
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

    return result_text


def build_recommendation_text(ai_result) -> str | None:
    """Build the RAG recommendation message, or None if there is none."""
    if not (ai_result and ai_result.rag_recommendation):
        return None
    text = str(M.AI_RECOMMENDATION).format(
        rag_recommendation=html.escape(ai_result.rag_recommendation),
    )
    if ai_result.sources:
        sources_text = "\n".join(html.escape(s) for s in ai_result.sources)
        text += str(M.AI_SOURCES).format(sources=sources_text)
    return text
