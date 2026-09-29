from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Code, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import VERDICT_TEXT

if TYPE_CHECKING:
    from apps.bot.user_data import AIResult

# Telegram's cap on a message's text
_MESSAGE_LIMIT = 4096


def _units(value: str) -> int:
    """In UTF-16 units, as Telegram counts; never under a plain len()."""
    return len(value.encode("utf-16-le")) // 2


def _length(text: Text) -> int:
    return _units(text.render()[0])


def _cut(value: str, units: int) -> str:
    """The longest start of value within units; a split emoji is dropped whole."""
    return value.encode("utf-16-le")[: units * 2].decode("utf-16-le", errors="ignore")


def build_saving_text() -> Text:
    return Text("⏳ ", _("Saving…"))


def build_ai_analyzing_text() -> Text:
    return Text("🤖 ", _("Running AI analysis…"))


def build_save_failed_text() -> Text:
    return Text("❌ ", _("An error occurred. Please try again."))


def _ai_section(ai_result: AIResult | None) -> Text:
    if not (ai_result and ai_result.defect_class):
        return Text("ℹ️ ", _("AI analysis is not available."))
    confidence = int((ai_result.confidence or 0) * 100)
    # An unknown verdict still renders
    emoji, verdict = VERDICT_TEXT.get(ai_result.verdict, ("ℹ️", "-"))
    return as_list(
        Text("🤖 ", Bold(_("AI Analysis:"))),
        Text("📌 ", ai_result.defect_class),
        Text("📊 ", _("Confidence:"), " ", f"{confidence}%"),
        Text(emoji, " ", _("AI verdict:"), " ", Code(verdict)),
    )


def build_result_text(ai_result: AIResult | None) -> Text:
    return as_list(
        Text("✅ ", Bold(_("Defect registered successfully!"))),
        _ai_section(ai_result),
        sep="\n\n",
    )


def _recommendation(recommendation: str, sources: list[str]) -> Text:
    parts = [as_list(Text("💡 ", Bold(_("Recommendation:"))), recommendation)]
    if sources:
        parts.append(as_list(Text("📎 ", Bold(_("Sources:"))), *sources))
    return as_list(*parts, sep="\n\n")


def build_recommendation_text(ai_result: AIResult | None) -> Text | None:
    """Cut short with an ellipsis where it alone would pass the cap."""
    if not (ai_result and ai_result.rag_recommendation):
        return None
    recommendation, sources = ai_result.rag_recommendation, ai_result.sources
    text = _recommendation(recommendation, sources)
    overflow = _length(text) - _MESSAGE_LIMIT
    if overflow > 0:
        kept = _units(recommendation) - overflow - 1
        text = _recommendation(_cut(recommendation, kept) + "…", sources)
    return text


def build_result_messages(ai_result: AIResult | None) -> list[Text]:
    """One message, or the recommendation apart when together they pass the cap."""
    result = build_result_text(ai_result)
    recommendation = build_recommendation_text(ai_result)
    if recommendation is None:
        return [result]
    together = as_list(result, recommendation, sep="\n\n")
    if _length(together) <= _MESSAGE_LIMIT:
        return [together]
    return [result, recommendation]
