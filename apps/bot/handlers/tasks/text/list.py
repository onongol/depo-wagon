from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import LIST_NUMBER_EMOJI

from .utils import severity_emoji, status_text, wagon_and_node


def build_no_tasks_text() -> Text:
    return Text("✅ ", _("You have no open defects."))


def build_text_list(defects: list, page: int, total: int, pages: int) -> Text:
    """The defect list, numbered to match the buttons under it."""
    counter = str(_("{total} total, page {page}/{pages}")).format(
        total=total, page=page + 1, pages=pages
    )

    blocks = [Text("📋 ", Bold(_("Open Defects")), f" ({counter})")]

    for keycap, defect in zip(LIST_NUMBER_EMOJI, defects, strict=False):
        inspector = defect.inspector.short_name if defect.inspector else "-"
        inspected_at = (
            defect.inspected_at.strftime("%Y-%m-%d") if defect.inspected_at else "-"
        )

        blocks.append(
            Text(
                f"{keycap} {severity_emoji(defect)} ",
                wagon_and_node(defect),
                f" ({defect.get_defect_type_display()})\n",
                f"{status_text(defect.status)}",
                f" | 👤 {inspector}",
                f" | 🕐 {inspected_at}",
            )
        )

    return as_list(*blocks, sep="\n\n")
