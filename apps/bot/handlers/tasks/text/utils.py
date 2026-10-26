from aiogram.utils.formatting import Bold

from apps.bot.constants import SEVERITY_EMOJI, STATUS_EMOJI
from apps.bot.utils.choices import emoji_label
from apps.defects.constants import DefectStatus


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def status_text(value: str) -> str:
    return emoji_label(STATUS_EMOJI, DefectStatus, value)


def severity_emoji(defect) -> str:
    return SEVERITY_EMOJI.get(defect.severity, "⚪")


def wagon_and_node(defect) -> Bold:
    return Bold(defect.wagon.number, " - ", defect.get_node_display())
