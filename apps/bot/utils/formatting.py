from aiogram.utils.formatting import Bold, ExpandableBlockQuote, Text, as_list


def quoted(emoji: str, label, *body) -> Text:
    """A bold label over a quote that folds long text away until tapped."""
    return as_list(Text(emoji, " ", Bold(label, ":")), ExpandableBlockQuote(*body))
