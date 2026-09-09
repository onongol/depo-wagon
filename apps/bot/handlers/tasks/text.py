import html

from apps.bot.constants import SEVERITY_EMOJI, STATUS_LABEL, TASKS_PAGE_SIZE
from apps.bot.messages import BotMessages as M


def build_text(defects: list, page: int, total: int) -> str:
    """Build the defect list message text."""
    start = page * TASKS_PAGE_SIZE + 1
    end = min((page + 1) * TASKS_PAGE_SIZE, total)
    lines = [
        str(M.TASKS_HEADER).format(total=total, start=start, end=end),
    ]

    for d in defects:
        sev_emoji = SEVERITY_EMOJI.get(d.severity, "⚪")
        status_str = str(STATUS_LABEL.get(d.status, d.status))
        inspector = html.escape(d.inspector.short_name) if d.inspector else "—"
        number = html.escape(d.wagon.number)
        node = d.get_node_display()
        defect_type = d.get_defect_type_display()
        inspected_at = d.inspected_at.strftime("%Y-%m-%d") if d.inspected_at else "—"
        lines.append(
            f"{sev_emoji} <b>{number}</b> — {node}\n"
            f"   {defect_type} | {status_str}\n"
            f"   👤 {inspector} | 🕐 {inspected_at}"
        )

    return "\n".join(lines)
