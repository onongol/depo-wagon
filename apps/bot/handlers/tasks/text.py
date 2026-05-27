from apps.bot.messages import BotMessages as M

from .constants import PAGE_SIZE, SEVERITY_EMOJI, STATUS_LABEL


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
        inspector = d.inspector.short_name if d.inspector else "—"
        lines.append(
            f"{sev_emoji} <b>{d.wagon.number}</b> — {d.get_node_display()}\n"
            f"   {d.get_defect_display()} | {status_str}\n"
            f"   👤 {inspector} | 🕐 {d.inspected_at.strftime('%Y-%m-%d %H:%M')}"
        )

    return "\n".join(lines)
