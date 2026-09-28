from django.utils.translation import gettext_lazy as _


class DefectMessages:
    """The whole step-by-step defect registration flow and AI results."""

    # ── Edit from summary ────────────────────────────────────────────────────

    EDIT_SEVERITY = _("✏️ Select severity:")
    EDIT_DESCRIPTION = _("✏️ Enter the description (or skip):")

    # ── Description ──────────────────────────────────────────────────────────

    ASK_DESCRIPTION = _("📝 Enter a description of the defect (or skip):")

    DESCRIPTION_TOO_LONG = _(
        "❌ Description is too long ({length}/{max} characters).\n\nPlease shorten it:"
    )

    # ── Confirm + AI ─────────────────────────────────────────────────────────

    SAVING = _("⏳ Saving...")

    AI_ANALYZING = _("🤖 Running AI analysis...")

    SAVE_SUCCESS = _(
        "✅ <b>Defect registered successfully!</b>\n🆔 <code>{short_id}...</code>\n"
    )

    AI_RESULT = _(
        "\n🤖 <b>AI Analysis:</b>\n"
        "📌 {defect_class}\n"
        "📊 Confidence: {confidence}%\n"
        "{verdict_emoji} AI verdict: <code>{verdict}</code>"
    )

    AI_RECOMMENDATION = _("\n\n💡 <b>Recommendation</b>:\n{rag_recommendation}")

    AI_SOURCES = _("\n\n📎 <b>Sources:</b>\n{sources}")

    AI_UNAVAILABLE = _("\nℹ️ AI analysis is not available.")

    ASK_EMPLOYEE_VERDICT = _("\n\n👨‍🔧 <b>Your verdict:</b>")

    SAVE_FAILED = _("❌ An error occurred. Please try again.")

    DEFECT_CANCELLED = _("❌ Defect registration cancelled.")

    FORM_OUTDATED = _(
        "♻️ The bot was updated while you were filling this in, so the form "
        "could not be carried over.\n\nSorry — please start it again."
    )

    # ── Employee verdict ─────────────────────────────────────────────────────

    VERDICT_DONE = _("<b>Your verdict:</b> {label}\n\n📋 Registration complete.")

    DECOMMISSION_ALERT = _(
        "🔴 <b>Decommission Proposal</b>\n\n"
        "🚃 Wagon: <b>{wagon_number}</b>\n"
        "🔧 Node: {node_label}\n"
        "⚠️ Defect: {defect_type_label}\n"
        "👤 Inspector: {inspector_name}\n\n"
        "This wagon is recommended for decommission.\n"
        "Please review in App."
    )
