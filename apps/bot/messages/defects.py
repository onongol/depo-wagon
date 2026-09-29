from django.utils.translation import gettext_lazy as _


class DefectMessages:
    """The defect flow's texts not yet moved to its text/ builders."""

    DEFECT_CANCELLED = _("❌ Defect registration cancelled.")

    FORM_OUTDATED = _(
        "♻️ The bot was updated while you were filling this in, so the form "
        "could not be carried over.\n\nSorry — please start it again."
    )

    # ── Decommission ─────────────────────────────────────────────────────────

    DECOMMISSION_ALERT = _(
        "🔴 <b>Decommission Proposal</b>\n\n"
        "🚃 Wagon: <b>{wagon_number}</b>\n"
        "🔧 Node: {node_label}\n"
        "⚠️ Defect: {defect_type_label}\n"
        "👤 Inspector: {inspector_name}\n\n"
        "This wagon is recommended for decommission.\n"
        "Please review in App."
    )
