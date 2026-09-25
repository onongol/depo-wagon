from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

_SELECT_TYPE = _("Select the defect type:")


def build_edit_defect_type_text() -> Text:
    return Text("✏️ ", _SELECT_TYPE)


def build_part_number_confirmed_text(part_number: str) -> Text:
    return as_list(
        Text("✅ ", _("Part number:"), " ", Bold(part_number)),
        _SELECT_TYPE,
        sep="\n\n",
    )


def build_part_number_skipped_text() -> Text:
    return as_list(Text("⏭ ", _("Part number skipped.")), _SELECT_TYPE, sep="\n\n")


def build_defect_type_confirmed_text(label: str) -> Text:
    return as_list(
        Text("✅ ", _("Defect type:"), " ", Bold(label)),
        _("Select severity:"),
        sep="\n\n",
    )
