from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Text, as_list
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import SEVERITY_LABELS, VERDICT_LABELS
from apps.bot.utils.defect_fields import (
    DefectFields,
    build_ai_section,
    build_defect_fields,
    field_row,
    measurement_line,
)
from apps.defects.constants import DefectType

from .utils import status_text, truncate

if TYPE_CHECKING:
    from apps.bot.services.defect_card import DefectCard

CARD_MAX_MEASUREMENTS = 10
CARD_MAX_DESCRIPTION = 600


def _card_fields(card: DefectCard) -> DefectFields:
    """The form's fields, from the saved defect."""
    defect = card.defect
    shown = card.measurements[:CARD_MAX_MEASUREMENTS]
    responsible = defect.responsible_employee
    return DefectFields(
        wagon=defect.wagon.number,
        department=defect.get_department_display(),
        node=defect.get_node_display(),
        part_number=defect.part_number,
        defect_type=defect.get_defect_type_display(),
        # The form asks for one only for a human factor
        responsible=(
            responsible.full_name
            if responsible and defect.defect_type == DefectType.HUMAN_FACTOR
            else None
        ),
        # A float, so a stored 3.50 reads as the 3.5 the form showed
        measurements=tuple(
            measurement_line(m.get_dimension_display(), float(m.value), m.unit)
            for m in shown
        ),
        measurements_hidden=len(card.measurements) - len(shown),
        photos=card.photo_count,
        description=truncate(defect.description, CARD_MAX_DESCRIPTION),
        severity=SEVERITY_LABELS.get(defect.severity, defect.severity),
        verdict=str(VERDICT_LABELS.get(defect.verdict, defect.verdict)),
    )


def build_card_text(card: DefectCard) -> Text:
    """The card of one defect, laid out as the form that registered it."""
    defect = card.defect
    inspected_at = (
        timezone.localtime(defect.inspected_at).strftime("%Y-%m-%d %H:%M")
        if defect.inspected_at
        else None
    )

    return as_list(
        Text("📋 ", Bold(_("Defect card"))),
        as_list(
            field_row("📊", _("Status:"), status_text(defect.status)),
            field_row(
                "👤",
                _("Inspector:"),
                defect.inspector.full_name if defect.inspector else None,
            ),
            field_row("🕐", _("Date:"), inspected_at),
        ),
        as_list(*build_defect_fields(_card_fields(card))),
        build_ai_section(
            defect.ai_defect_class, defect.ai_confidence, defect.ai_verdict
        ),
        sep="\n\n",
    )


def build_defect_unavailable_toast() -> str:
    """Plain text: a callback answer carries no entities."""
    return f"⚠️ {_('This defect is no longer available.')}"
