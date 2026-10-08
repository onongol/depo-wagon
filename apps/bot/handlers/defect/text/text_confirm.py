from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.user_data import AIResult
from apps.bot.utils.defect_fields import build_ai_section
from apps.bot.utils.formatting import MESSAGE_LIMIT, quoted, utf16_cut, utf16_len

from .text_screen import build_screen_text


def _length(text: Text) -> int:
    return utf16_len(text.render()[0])


def _progress_heading() -> Text:
    return Text("📋 ", Bold(_("Defect Summary:")))


def build_saving_text(fields: list[Text]) -> Text:
    return build_screen_text(_progress_heading(), fields, Text("⏳ ", _("Saving…")))


def build_ai_analyzing_text(fields: list[Text]) -> Text:
    return build_screen_text(
        _progress_heading(), fields, Text("🤖 ", _("Running AI analysis…"))
    )


def build_save_failed_text() -> Text:
    return Text("❌ ", _("An error occurred. Please try again."))


def build_result_text(fields: list[Text], ai_result: AIResult | None) -> Text:
    ai = ai_result or AIResult()
    return build_screen_text(
        Text("✅ ", Bold(_("Defect registered successfully!"))),
        fields,
        build_ai_section(ai.defect_class, ai.confidence, ai.verdict),
    )


def _recommendation(recommendation: str, sources: list[str]) -> Text:
    parts = [quoted("💡", _("Recommendation"), recommendation)]
    if sources:
        parts.append(as_list(Text("📎 ", Bold(_("Sources:"))), *sources))
    return as_list(*parts, sep="\n\n")


def build_recommendation_text(ai_result: AIResult | None) -> Text | None:
    """Cut short with an ellipsis where it alone would pass the cap."""
    if not (ai_result and ai_result.rag_recommendation):
        return None
    recommendation, sources = ai_result.rag_recommendation, ai_result.sources
    text = _recommendation(recommendation, sources)
    overflow = _length(text) - MESSAGE_LIMIT
    if overflow > 0:
        kept = utf16_len(recommendation) - overflow - 1
        text = _recommendation(utf16_cut(recommendation, kept) + "…", sources)
    return text


def build_result_messages(fields: list[Text], ai_result: AIResult | None) -> list[Text]:
    """One message, or the recommendation apart when together they pass the cap."""
    result = build_result_text(fields, ai_result)
    recommendation = build_recommendation_text(ai_result)
    if recommendation is None:
        return [result]
    together = as_list(result, recommendation, sep="\n\n")
    if _length(together) <= MESSAGE_LIMIT:
        return [together]
    return [result, recommendation]
