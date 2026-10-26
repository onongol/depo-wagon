from aiogram.utils.formatting import Bold, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _

_PAGE = _("Page {page}/{total} • {count} employees")
_FOUND = _("Found {count} employee(s)")


def build_ask_responsible_employee_text(page: int, total: int, count: int) -> Text:
    return as_list(
        Text("👤 ", _("Select the responsible employee:")),
        Text("📄 ", str(_PAGE).format(page=page, total=total, count=count)),
        Italic(_("Type a name to search:")),
    )


def build_responsible_employee_search_text(query: str, count: int) -> Text:
    return as_list(
        Text("🔍 ", _("Search:"), " ", Bold(query)),
        str(_FOUND).format(count=count),
        Italic(_("Type a new name to search again:")),
    )
