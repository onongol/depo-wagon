from aiogram.utils.formatting import (
    Bold,
    Code,
    ExpandableBlockQuote,
    Text,
    as_key_value,
    as_list,
)

from apps.bot.constants import SEVERITY_EMOJI, STATUS_LABEL, VERDICT_TEXT


def field(emoji: str, label, value) -> Text:
    # A dash stands for a missing value; 0 is a value, not a gap.
    if value is None or value == "":
        value = "-"
    return Text(emoji, " ", as_key_value(label, value))


def quoted(emoji: str, label, *body) -> Text:
    return as_list(Text(emoji, " ", Bold(label, ":")), ExpandableBlockQuote(*body))


def code(value: str) -> Text | str:
    return Code(value) if value else "-"


def truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def status_text(value: str) -> str:
    return str(STATUS_LABEL.get(value, value))


def severity_emoji(defect) -> str:
    return SEVERITY_EMOJI.get(defect.severity, "⚪")


def verdict_text(value: str) -> str:
    if value not in VERDICT_TEXT:
        return "-"
    emoji, label = VERDICT_TEXT[value]
    return f"{emoji} {label!s}"


def wagon_and_node(defect) -> Bold:
    return Bold(defect.wagon.number, " - ", defect.get_node_display())
