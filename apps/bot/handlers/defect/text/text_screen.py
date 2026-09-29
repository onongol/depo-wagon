from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.states import DefectSG

from .text_measurement import build_measurement_line

if TYPE_CHECKING:
    from collections.abc import Collection

    from apps.bot.user_data import DefectData

_STEP = _("Defect Summary (Step {step} of {total}):")
_SKIPPED = "—"


def build_step_heading(step: int, total: int) -> Text:
    return Text("📋 ", Bold(str(_STEP).format(step=step, total=total)))


def build_editing_heading() -> Text:
    return Text("📋 ", Bold(_("Defect Summary (editing):")))


def build_review_heading() -> Text:
    return Text("📋 ", Bold(_("Defect Summary — please review:")))


def build_save_question_text() -> Text:
    return Text(_("Save?"))


def build_stray_input_text() -> Text:
    return Text("👇 ", _("This step doesn't take that. Please answer below."))


def _bold(value: str | None) -> Bold | None:
    return Bold(value) if value else None


def _measurements(form: DefectData) -> Text | None:
    if not form.measurements:
        return None
    lines = (Text("🔹 ", build_measurement_line(m)) for m in form.measurements)
    return as_list(Text(len(form.measurements)), *lines)


def build_fields(form: DefectData, behind: Collection[str]) -> list[Text]:
    """What the form holds, in order; a field a step behind left empty is a dash."""
    rows = (
        (DefectSG.wagon_num, "🚃", _("Wagon:"), _bold(form.wagon_number)),
        (DefectSG.department, "🏭", _("Department:"), _bold(form.department_label)),
        (DefectSG.node, "🔧", _("Node:"), _bold(form.node_label)),
        (DefectSG.part_number, "🔢", _("Part number:"), _bold(form.part_number)),
        (DefectSG.defect_type, "⚠️", _("Defect type:"), _bold(form.defect_type_label)),
        (
            DefectSG.responsible_employee,
            "👤",
            _("Responsible:"),
            _bold(form.responsible_employee_label),
        ),
        (DefectSG.measurement_choice, "📐", _("Measurements:"), _measurements(form)),
        (DefectSG.photo, "📸", _("Photos:"), len(form.photos) or None),
        (DefectSG.desc, "📝", _("Description:"), form.description or None),
        (DefectSG.severity, "🌡️", _("Severity:"), _bold(form.severity_label)),
    )
    return [
        Text(emoji, " ", label, " ", _SKIPPED if value is None else value)
        for step, emoji, label, value in rows
        if value is not None or step.state in behind
    ]


def build_screen_text(
    heading: Text,
    fields: list[Text],
    question: Text,
    *,
    notice: Text | None = None,
) -> Text:
    """The heading, the form so far, a notice such as an error, and the question."""
    parts = [heading]
    if fields:
        parts.append(as_list(*fields))
    if notice:
        parts.append(notice)
    parts.append(question)
    return as_list(*parts, sep="\n\n")
