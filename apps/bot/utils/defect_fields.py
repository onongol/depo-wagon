from dataclasses import dataclass
from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Code, ExpandableBlockQuote, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import VERDICT_TEXT
from apps.bot.states import DefectSG

if TYPE_CHECKING:
    from collections.abc import Collection
    from decimal import Decimal

_SKIPPED = "—"


@dataclass(frozen=True)
class DefectFields:
    """A defect as its screens show it: the form being filled, or a saved defect."""

    wagon: str | None = None
    department: str | None = None
    node: str | None = None
    part_number: str | None = None
    defect_type: str | None = None
    responsible: str | None = None
    measurements: tuple[Text, ...] = ()
    photos: int = 0
    description: str | None = None
    severity: str | None = None
    verdict: str | None = None


def _bold(value: str | None) -> Bold | None:
    return Bold(value) if value else None


def measurement_line(label: str, value, unit: str) -> Text:
    line = Text(label, ": ", Bold(value))
    if unit:
        line = Text(line, " ", unit)
    return line


def _measurements(fields: DefectFields) -> Text | None:
    if not fields.measurements:
        return None
    lines = (Text("🔹 ", line) for line in fields.measurements)
    return as_list(Text(len(fields.measurements)), *lines)


def build_defect_fields(
    fields: DefectFields, behind: Collection[str] = ()
) -> list[Text]:
    """In the form's order; an empty field is left out, or a dash for a step behind."""
    rows = (
        (DefectSG.wagon_num, "🚃", _("Wagon:"), _bold(fields.wagon)),
        (DefectSG.department, "🏭", _("Department:"), _bold(fields.department)),
        (DefectSG.node, "🔧", _("Node:"), _bold(fields.node)),
        (DefectSG.part_number, "🔢", _("Part number:"), _bold(fields.part_number)),
        (DefectSG.defect_type, "⚠️", _("Defect type:"), _bold(fields.defect_type)),
        (
            DefectSG.responsible_employee,
            "👤",
            _("Responsible:"),
            _bold(fields.responsible),
        ),
        (DefectSG.measurement_choice, "📐", _("Measurements:"), _measurements(fields)),
        (DefectSG.photo, "📸", _("Photos:"), fields.photos or None),
        (
            DefectSG.desc,
            "📝",
            _("Description:"),
            Text("\n", ExpandableBlockQuote(fields.description))
            if fields.description
            else None,
        ),
        (DefectSG.severity, "🌡️", _("Severity:"), _bold(fields.severity)),
        (DefectSG.employee_verdict, "👨‍🔧", _("Verdict:"), _bold(fields.verdict)),
    )
    return [
        Text(emoji, " ", label, " ", _SKIPPED if value is None else value)
        for step, emoji, label, value in rows
        if value is not None or step.state in behind
    ]


def build_ai_section(
    defect_class: str, confidence: float | Decimal | None, verdict: str
) -> Text:
    if not defect_class:
        return Text("ℹ️ ", _("AI analysis is not available."))
    percent = int((confidence or 0) * 100)
    # An unknown verdict still renders
    emoji, label = VERDICT_TEXT.get(verdict, ("ℹ️", "-"))
    return as_list(
        Text("🤖 ", Bold(_("AI Analysis:"))),
        Text(_("Defect class:")),
        ExpandableBlockQuote(defect_class),
        Text(_("Confidence:"), " ", f"{percent}%"),
        Text(_("AI verdict:"), " ", emoji, " ", Code(label)),
    )
