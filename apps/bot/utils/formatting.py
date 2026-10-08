from aiogram.utils.formatting import Bold, ExpandableBlockQuote, Text, as_list

# Telegram's cap on a message's text, in UTF-16 units
MESSAGE_LIMIT = 4096


def utf16_len(value: str) -> int:
    """In UTF-16 units, as Telegram counts; never under a plain len()."""
    return len(value.encode("utf-16-le")) // 2


def utf16_cut(value: str, units: int) -> str:
    """The longest start of value within units; a split emoji is dropped whole."""
    return value.encode("utf-16-le")[: units * 2].decode("utf-16-le", errors="ignore")


def quoted(emoji: str, label, *body) -> Text:
    """A bold label over a quote that folds long text away until tapped."""
    return as_list(Text(emoji, " ", Bold(label, ":")), ExpandableBlockQuote(*body))
