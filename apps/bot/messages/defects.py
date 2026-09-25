from django.utils.translation import gettext_lazy as _


class DefectMessages:
    """The whole step-by-step defect registration flow and AI results."""

    # ── Responsible employee / severity ──────────────────────────────────────

    ASK_RESPONSIBLE_EMPLOYEE = _(
        "👤 Select the responsible employee:\n"
        "📄 Page {page}/{total} • {count} employees\n"
        "<i>Type a name to search:</i>"
    )

    ASK_RESPONSIBLE_EMPLOYEE_SEARCH = _(
        "🔍 Search: <b>{query}</b>\n"
        "Found {count} employee(s)\n"
        "<i>Type a new name to search again:</i>"
    )

    RESPONSIBLE_EMPLOYEE_CONFIRMED = _(
        "✅ Responsible employee: <b>{label}</b>\n\n📝 Enter a description (or skip):"
    )

    SEVERITY_CONFIRMED = _(
        "✅ Severity: <b>{label}</b>\n\n📸 Send a photo of the defect (or skip):"
    )

    # ── Edit from summary ────────────────────────────────────────────────────

    EDIT_SEVERITY = _("✏️ Select severity:")
    EDIT_DESCRIPTION = _("✏️ Enter the description (or skip):")

    # ── Photo ────────────────────────────────────────────────────────────────

    PHOTO_RECEIVED = _(
        "✅ Photo {count} received.\n\n📸 Send another photo or press Done:"
    )

    PHOTO_ALBUM_RECEIVING = _(
        "📸 Receiving the album.\n\nSend more photos or press Done when finished:"
    )

    PHOTOS_ATTACHED = _("✅ Photos attached: {count}")

    PHOTO_TOO_LARGE = _(
        "⚠️ Photo is too large (max 10 MB). Please send a smaller photo:"
    )

    # ── Measurement sub-flow ─────────────────────────────────────────────────

    ASK_MEASUREMENT = _("📐 Would you like to add a measurement?")

    ASK_DIMENSION = _("📏 Select the measurement dimension:")

    DIMENSION_CONFIRMED = _(
        "✅ Dimension: <b>{label}</b>\n\nEnter the measurement value <i>(e.g. 12.5)</i>:"
    )

    VALUE_INVALID = _("❌ Please enter a number <i>(e.g. 12.5)</i>:")

    ASK_NORM = _("📋 Enter the norm value (or skip):")

    NORM_INVALID = _("❌ Please enter a number <i>(e.g. 10.0)</i> (or skip):")

    ASK_UNIT = _("📌 Enter the measurement unit <i>(e.g. mm, cm, °)</i> (or skip):")

    UNIT_TOO_LONG = _(
        "❌ Unit is too long ({length}/{max} characters).\n\nPlease shorten it (or skip):"
    )

    MEASUREMENT_SAVED = _(
        "✅ Measurement {count} saved: <b>{label}</b> = {value}{unit}\n\nAdd another?"
    )

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
