from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.utils.choices import choice_label
from apps.defects.constants import DefectNode, DefectType

if TYPE_CHECKING:
    from apps.bot.user_data import DefectData
    from apps.core.models import Employee


def build_decommission_alert_text(form: DefectData, inspector: Employee) -> Text:
    return as_list(
        Text("🔴 ", Bold(_("Decommission Proposal"))),
        as_list(
            Text("🚃 ", _("Wagon:"), " ", form.wagon_number or "—"),
            Text("🔧 ", _("Node:"), " ", choice_label(DefectNode, form.node) or "—"),
            Text(
                "⚠️ ",
                _("Defect:"),
                " ",
                choice_label(DefectType, form.defect_type) or "—",
            ),
            Text("👤 ", _("Inspector:"), " ", inspector.full_name),
        ),
        as_list(
            _("This wagon is recommended for decommission."),
            _("Please review in App."),
        ),
        sep="\n\n",
    )
