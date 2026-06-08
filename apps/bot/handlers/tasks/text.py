import html

from apps.bot.constants import PAGE_SIZE, SEVERITY_EMOJI, STATUS_LABEL
from apps.bot.messages import BotMessages as M


def build_text(defects: list, page: int, total: int) -> str:
    """Build the defect list message text."""
    start = page * PAGE_SIZE + 1
    end = min((page + 1) * PAGE_SIZE, total)
    lines = [
        str(M.TASKS_HEADER).format(total=total, start=start, end=end),
    ]

    for d in defects:
        sev_emoji = SEVERITY_EMOJI.get(d.severity, "⚪")
        status_str = str(STATUS_LABEL.get(d.status, d.status))
        inspector = html.escape(d.inspector.short_name) if d.inspector else "—"
        lines.append(
            f"{sev_emoji} <b>{html.escape(d.wagon.number)}</b> — {d.get_node_display()}\n"
            f"   {d.get_defect_type_display()} | {status_str}\n"
            f"   👤 {inspector} | 🕐 {d.inspected_at.strftime('%Y-%m-%d')}"
        )

    return "\n".join(lines)
