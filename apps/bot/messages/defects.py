from django.utils.translation import gettext_lazy as _


class DefectMessages:
    """The whole step-by-step defect registration flow, AI results and tasks."""

    NOT_REGISTERED = _("❌ Please register first using /start.")

    NEW_DEFECT_START = _(
        "🔍 <b>New Defect Registration</b>\n\nEnter the wagon number:\n"
        "<i>(e.g. 12345678)</i>"
    )

    # ── Wagon ────────────────────────────────────────────────────────────────

    WAGON_NUM_PROMPT = _(
        "⬆️ Please enter the wagon number:\n<i>(e.g. 12345678)</i>\n\n"
        "To exit, type /cancel."
    )

    WAGON_NOT_FOUND = _(
        "❌ Wagon <code>{number}</code> not found.\n\nPlease check and try again:"
    )

    WAGON_CONFIRMED = _("✅ Wagon: <b>{number}</b>\n\nSelect the department:")

    # ── Department / node / part / type / severity ───────────────────────────

    DEPARTMENT_CONFIRMED = _("✅ Department: <b>{label}</b>\n\nSelect the defect node:")

    NODE_CONFIRMED = _("✅ Node: <b>{label}</b>\n\nEnter the part number (or skip):")

    PART_NUMBER_PROMPT = _("🔢 Enter the part number <i>(e.g. ABC-1234)</i> or skip:")

    PART_NUMBER_CONFIRMED = _(
        "✅ Part number: <b>{part_number}</b>\n\nSelect the defect type:"
    )

    PART_NUMBER_SKIPPED = _("⏭ Part number skipped.\n\nSelect the defect type:")

    DEFECT_TYPE_CONFIRMED = _("✅ Defect type: <b>{label}</b>\n\nSelect severity:")

    DEFECT_TYPE_HUMAN_FACTOR = _(
        "✅ Defect type: <b>{label}</b>\n\n📸 Send a photo (or skip):"
    )

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

    EDIT_WAGON = _("✏️ Enter the new wagon number:")
    EDIT_NODE = _("✏️ Select the node:")
    EDIT_PART_NUMBER = _("✏️ Enter the part number (or skip):")
    EDIT_DEFECT_TYPE = _("✏️ Select the defect type:")
    EDIT_SEVERITY = _("✏️ Select severity:")
    EDIT_DESCRIPTION = _("✏️ Enter the description (or skip):")

    # ── Photo ────────────────────────────────────────────────────────────────

    PHOTO_RECEIVED = _("✅ Photo {count} received.\n\n📸 Send another photo (or skip):")

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

    AI_UNAVAILABLE = _("\nℹ️ AI analysis is not available.")

    ASK_EMPLOYEE_VERDICT = _("\n\n👨‍🔧 <b>Your verdict:</b>")

    SAVE_FAILED = _("❌ An error occurred. Please try again.\n<code>{error}</code>")

    DEFECT_CANCELLED = _("❌ Defect registration cancelled.")

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

    # ── Tasks (my_tasks) ─────────────────────────────────────────────────────

    TASKS_HEADER = _("📋 <b>Open Defects</b> ({total} total, {start}–{end})\n")

    NO_TASKS = _("✅ You have no open defects.")

    STATUS_CHANGED = _("✅ Status updated to <b>{status}</b>.")

    STATUS_CHANGE_FAILED = _("❌ Failed to update status: <code>{error}</code>")
