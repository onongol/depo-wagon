import html

from django.utils.translation import gettext_lazy as _

from apps.bot.user_data import DefectData


def build_summary(defect: DefectData) -> str:
    """Build a human-readable defect summary for the confirmation step."""
    lines = [
        str(_("📋 <b>Defect Summary — please review:</b>\n")),
        str(_("🚃 Wagon: <b>{wagon}</b>")).format(wagon=defect.wagon_number or "?"),
        str(_("🔧 Node: <b>{node}</b>")).format(node=defect.node_label or "?"),
        str(_("⚠️ Defect type: <b>{dtype}</b>")).format(
            dtype=defect.defect_type_label or "?"
        ),
        str(_("🔴 Severity: <b>{severity}</b>")).format(
            severity=defect.severity_label or "?"
        ),
    ]

    if defect.measurements:
        lines.append(
            str(_("📐 Measurements: {count}")).format(count=len(defect.measurements))
        )
        for measurement in defect.measurements:
            mline = f"  • {measurement.dimension_label} = {measurement.value}"
            if measurement.unit:
                mline += f" {measurement.unit}"
            if measurement.norm_value is not None:
                mline += " " + str(_("<i>(norm: {norm})</i>")).format(
                    norm=measurement.norm_value
                )
            lines.append(mline)

    if defect.photo_file_ids:
        lines.append(
            str(_("📸 Photos: {count}")).format(count=len(defect.photo_file_ids))
        )

    if defect.description:
        lines.append(
            str(_("📝 Description: {desc}")).format(
                desc=html.escape(defect.description)
            )
        )

    lines.append("\n" + str(_("Save?")))
    return "\n".join(lines)
