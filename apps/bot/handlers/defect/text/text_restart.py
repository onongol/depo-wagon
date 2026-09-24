from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_defect_in_progress_text() -> Text:
    return as_list(
        Text("⚠️ ", Bold(_("You are already registering a defect."))),
        _(
            "Continue where you left off, or start a new one? "
            "Anything not yet saved will be lost."
        ),
        sep="\n\n",
    )


def build_defect_continued_text() -> Text:
    return Text("👌 ", _("Carry on from the last step above."))
