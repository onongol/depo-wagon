import html

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from apps.bot.user_data import DefectData


def build_summary(defect: DefectData) -> str:
    """Build a human-readable defect summary for the confirmation step."""
    lines = [
        str(_("📋 <b>Defect Summary — please review:</b>\n")),
        format_lazy(_("🚃 Wagon: <b>{wagon}</b>"), wagon=defect.wagon_number or "?"),
        format_lazy(
            _("🏭 Department: <b>{dept}</b>"), dept=defect.department_label or "?"
        ),
        format_lazy(_("🔧 Node: <b>{node}</b>"), node=defect.node_label or "?"),
    ]

    if defect.part_number:
        lines.append(
            format_lazy(
                _("🔢 Part number: <b>{part}</b>"),
                part=html.escape(defect.part_number),
            )
        )

    lines.append(
        format_lazy(
            _("⚠️ Defect type: <b>{dtype}</b>"), dtype=defect.defect_type_label or "?"
        )
    )

    lines.append(
        format_lazy(
            _("🔴 Severity: <b>{severity}</b>"), severity=defect.severity_label or "?"
        )
    )

    if defect.responsible_employee_label:
        lines.append(
            format_lazy(
                _("👤 Responsible: <b>{emp}</b>"),
                emp=html.escape(defect.responsible_employee_label),
            )
        )

    if defect.measurements:
        lines.append(
            format_lazy(_("📐 Measurements: {count}"), count=len(defect.measurements))
        )
        for measurement in defect.measurements:
            dim = html.escape(str(measurement.dimension_label))
            val = html.escape(str(measurement.value))

            entry = f"🔹 {dim}: <b>{val}</b>"

            if measurement.unit:
                entry += f" {html.escape(measurement.unit)}"

            if measurement.norm_value is not None:
                norm_str = str(
                    format_lazy(
                        _("<i>(norm: {norm})</i>"),
                        norm=html.escape(str(measurement.norm_value)),
                    )
                )
                entry += " " + norm_str

            lines.append(entry)

    if defect.photo_file_ids:
        lines.append(
            format_lazy(_("📸 Photos: {count}"), count=len(defect.photo_file_ids))
        )

    if defect.description:
        lines.append(
            format_lazy(
                _("📝 Description: {desc}"), desc=html.escape(defect.description)
            )
        )

    lines.append("\n" + str(_("Save?")))
    return "\n".join(str(line) for line in lines)
