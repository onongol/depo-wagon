from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Italic, Text, as_list, as_marked_section
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.bot.utils.formatting import quoted

from .utils import (
    code,
    field,
    severity_emoji,
    status_text,
    truncate,
    verdict_text,
)

if TYPE_CHECKING:
    from apps.bot.services.defect_card import DefectCard

CARD_MAX_MEASUREMENTS = 10
CARD_MAX_DESCRIPTION = 600


def _measurement_line(measurement) -> Text:
    line = Text(measurement.get_dimension_display(), ": ", Bold(measurement.value))
    if measurement.unit:
        line = Text(line, " ", measurement.unit)
    if measurement.norm_value is not None:
        norm = str(_("(norm: {norm})")).format(norm=measurement.norm_value)
        line = Text(line, " ", Italic(norm))
    return line


def _measurements_block(measurements: list) -> Text:
    block = as_marked_section(
        Text("📐 ", Bold(_("Measurements"), ":")),
        *(_measurement_line(m) for m in measurements[:CARD_MAX_MEASUREMENTS]),
        marker="🔹 ",
    )

    hidden = len(measurements) - CARD_MAX_MEASUREMENTS
    if hidden > 0:
        return as_list(block, str(_("…and {count} more")).format(count=hidden))

    return block


def _ai_block(defect) -> Text | None:
    lines = []

    if defect.ai_defect_class:
        confidence = int((defect.ai_confidence or 0) * 100)
        lines.append(quoted("🤖", _("AI"), defect.ai_defect_class, f" ({confidence}%)"))

    if defect.ai_verdict:
        lines.append(field("⚖️", _("AI verdict"), verdict_text(defect.ai_verdict)))

    return as_list(*lines) if lines else None


def build_card_text(card: DefectCard) -> Text:
    """The card of one defect, from what get_defect_card already read."""
    defect = card.defect
    inspector = defect.inspector.full_name if defect.inspector else "-"
    inspected_at = (
        timezone.localtime(defect.inspected_at).strftime("%Y-%m-%d %H:%M")
        if defect.inspected_at
        else "-"
    )

    sections = [
        as_list(
            field("⚠️", _("Defect"), defect.get_defect_type_display()),
            field("📊", _("Status"), status_text(defect.status)),
            field(
                "🌡️",
                _("Severity"),
                severity_emoji(defect) + " " + defect.get_severity_display(),
            ),
        ),
        as_list(
            field("🚃", _("Wagon"), code(defect.wagon.number)),
            field("🏭", _("Department"), defect.get_department_display()),
            field("⚙️", _("Node"), defect.get_node_display()),
            field("🔢", _("Part number"), code(defect.part_number)),
        ),
        as_list(
            field("👤", _("Inspector"), inspector),
            field("🕐", _("Date"), inspected_at),
        ),
        field("📸", _("Photos"), card.photo_count),
    ]

    if responsible := defect.responsible_employee:
        sections.append(field("🧑‍🔧", _("Responsible"), responsible.full_name))

    if card.measurements:
        sections.append(_measurements_block(card.measurements))

    if defect.description:
        description = truncate(defect.description, CARD_MAX_DESCRIPTION)
        sections.append(quoted("📝", _("Description"), description))

    if ai := _ai_block(defect):
        sections.append(ai)

    if defect.verdict:
        sections.append(field("✍️", _("Verdict"), verdict_text(defect.verdict)))

    return as_list(*sections, sep="\n\n")
