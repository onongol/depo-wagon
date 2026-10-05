from django.utils.translation import gettext_lazy as _


class DefectMessages:
    """The defect flow's texts not yet moved to its text/ builders."""

    DEFECT_CANCELLED = _("❌ Defect registration cancelled.")

    FORM_OUTDATED = _(
        "♻️ The bot was updated while you were filling this in, so the form "
        "could not be carried over.\n\nSorry — please start it again."
    )
