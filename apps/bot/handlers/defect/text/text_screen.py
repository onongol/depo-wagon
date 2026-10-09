from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import SEVERITY_EMOJI, VERDICT_EMOJI
from apps.bot.utils.choices import emoji_label
from apps.bot.utils.defect_fields import DefectFields, build_defect_fields
from apps.defects.constants import DefectSeverity, DefectVerdict

from .text_measurement import build_measurement_line

if TYPE_CHECKING:
    from collections.abc import Collection

    from apps.bot.user_data import DefectData

_STEP = _("Defect Summary (Step {step} of {total}):")


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


def build_defect_cancelled_text() -> Text:
    return Text("❌ ", _("Defect registration cancelled."))


def build_fields(form: DefectData, behind: Collection[str]) -> list[Text]:
    """What the form holds, in order; a field a step behind left empty is a dash."""
    return build_defect_fields(
        DefectFields(
            wagon=form.wagon_number,
            department=form.department_label,
            node=form.node_label,
            part_number=form.part_number,
            defect_type=form.defect_type_label,
            responsible=form.responsible_employee_label,
            measurements=tuple(build_measurement_line(m) for m in form.measurements),
            photos=len(form.photos),
            description=form.description,
            severity=emoji_label(SEVERITY_EMOJI, DefectSeverity, form.severity),
            verdict=emoji_label(VERDICT_EMOJI, DefectVerdict, form.verdict),
        ),
        behind,
    )


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
