import html

from django.utils.translation import gettext_lazy as _


def build_summary(d: dict) -> str:
    """Build a human-readable defect summary for the confirmation step."""
    lines = [
        str(_("📋 <b>Defect Summary — please review:</b>\n")),
        str(_("🚃 Wagon: <b>{wagon}</b>")).format(wagon=d.get("wagon_number", "?")),
        str(_("🔧 Node: <b>{node}</b>")).format(node=d.get("node_label", "?")),
        str(_("⚠️ Defect type: <b>{dtype}</b>")).format(
            dtype=d.get("defect_type_label", "?")
        ),
        str(_("🔴 Severity: <b>{severity}</b>")).format(
            severity=d.get("severity_label", "?")
        ),
    ]

    measurements = d.get("measurements", [])
    if measurements:
        lines.append(str(_("📐 Measurements: {count}")).format(count=len(measurements)))
        for m in measurements:
            val = m.get("value")
            unit = m.get("unit", "")
            norm = m.get("norm_value")
            label = m.get("dimension_label", m.get("dimension", ""))
            mline = f"  • {label} = {val}"
            if unit:
                mline += f" {unit}"
            if norm is not None:
                mline += " " + str(_("<i>(norm: {norm})</i>")).format(norm=norm)
            lines.append(mline)

    photo_count = len(d.get("photo_file_ids", []))
    if photo_count:
        lines.append(str(_("📸 Photos: {count}")).format(count=photo_count))

    desc = d.get("description", "")
    if desc:
        lines.append(str(_("📝 Description: {desc}")).format(desc=html.escape(desc)))

    lines.append("\n" + str(_("Save?")))
    return "\n".join(lines)
