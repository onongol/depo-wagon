from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from django.db.models import TextChoices


def choice_label(
    choices: type[TextChoices], value: str | None, default: str | None = None
) -> str:
    """The value's label in the active language; an unknown value gives default."""
    try:
        return str(choices(value).label)
    except ValueError:
        return (value or "") if default is None else default


def emoji_label(
    emoji: Mapping[str, str], choices: type[TextChoices], value: str | None
) -> str:
    """The value as buttons and fields show it; an unknown value shows as is."""
    if value not in emoji:
        return value or ""
    return f"{emoji[value]} {choice_label(choices, value)}"


def emoji_choices(
    emoji: Mapping[str, str], choices: type[TextChoices]
) -> list[tuple[str, str]]:
    """(label, value) pairs for build_grid_keyboard, in the enum's order."""
    return [(emoji_label(emoji, choices, member), member.value) for member in choices]
