import html

from apps.bot.constants import VERDICT_TEXT
from apps.bot.messages import BotMessages as M


def _verdict_parts(value) -> tuple[str, str]:
    """Emoji and label; an unknown value still renders."""
    pair = VERDICT_TEXT.get(value)
    if pair is None:
        return "ℹ️", "-"
    return pair[0], str(pair[1])


def build_result_text(defect_id, verdict, ai_result) -> str:
    """The saved defect, the inspector's verdict, then the AI's on its own line."""
    result_text = str(M.SAVE_SUCCESS).format(short_id=str(defect_id)[:8])

    verdict_emoji, verdict_label = _verdict_parts(verdict)
    result_text += str(M.EMPLOYEE_VERDICT).format(
        verdict_emoji=verdict_emoji, verdict=verdict_label
    )

    if ai_result and ai_result.defect_class:
        confidence_pct = int((ai_result.confidence or 0) * 100)
        verdict_emoji, verdict_label = _verdict_parts(ai_result.verdict)

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
