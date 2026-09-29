from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Code, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import VERDICT_TEXT

if TYPE_CHECKING:
    from apps.bot.user_data import AIResult


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


def build_recommendation_text(ai_result: AIResult | None) -> Text | None:
    if not (ai_result and ai_result.rag_recommendation):
        return None
    parts = [
        as_list(Text("💡 ", Bold(_("Recommendation:"))), ai_result.rag_recommendation)
    ]
    if ai_result.sources:
        parts.append(as_list(Text("📎 ", Bold(_("Sources:"))), *ai_result.sources))
    return as_list(*parts, sep="\n\n")
