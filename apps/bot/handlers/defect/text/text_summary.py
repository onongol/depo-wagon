from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Text, as_list, as_marked_section
from django.utils.translation import gettext_lazy as _

from .text_measurement import build_measurement_line

if TYPE_CHECKING:
    from django.utils.functional import Promise

    from apps.bot.user_data import DefectData


def _field(emoji: str, label: str | Promise, value: str | None) -> Text:
    return Text(emoji, " ", label, " ", Bold(value or "?"))


def build_summary_text(defect: DefectData) -> Text:
    fields = [
        _field("🚃", _("Wagon:"), defect.wagon_number),
        _field("🏭", _("Department:"), defect.department_label),
        _field("🔧", _("Node:"), defect.node_label),
    ]
    if defect.part_number:
        fields.append(_field("🔢", _("Part number:"), defect.part_number))
    fields.append(_field("⚠️", _("Defect type:"), defect.defect_type_label))
    if defect.responsible_employee_label:
        fields.append(
            _field("👤", _("Responsible:"), defect.responsible_employee_label)
        )
    if defect.measurements:
        fields.append(
            as_marked_section(
                Text("📐 ", _("Measurements:"), " ", len(defect.measurements)),
                *(build_measurement_line(m) for m in defect.measurements),
                marker="🔹 ",
            )
        )
    if defect.photos:
        fields.append(Text("📸 ", _("Photos:"), " ", len(defect.photos)))
    if defect.description:
        fields.append(Text("📝 ", _("Description:"), " ", defect.description))
    fields.append(_field("🌡️", _("Severity:"), defect.severity_label))

    return as_list(
        Text("📋 ", Bold(_("Defect Summary — please review:"))),
        as_list(*fields),
        _("Save?"),
        sep="\n\n",
    )
