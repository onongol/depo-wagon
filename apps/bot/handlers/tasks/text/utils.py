from aiogram.utils.formatting import Bold

from apps.bot.constants import SEVERITY_EMOJI, STATUS_LABEL


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def status_text(value: str) -> str:
    return str(STATUS_LABEL.get(value, value))


def severity_emoji(defect) -> str:
    return SEVERITY_EMOJI.get(defect.severity, "⚪")


def wagon_and_node(defect) -> Bold:
    return Bold(defect.wagon.number, " - ", defect.get_node_display())
