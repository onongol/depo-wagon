from aiogram.utils.formatting import Bold, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.constants import (
    BTN_ASK,
    BTN_CANCEL,
    BTN_NEW_DEFECT,
    BTN_OPEN_DEFECTS,
    BTN_SAVE,
    LIST_NUMBER_EMOJI,
)


def build_help_text() -> Text:
    steps = (
        Text(_("Tap"), " ", Bold(BTN_NEW_DEFECT)),
        _("Enter 🚃 the wagon number"),
        _("Choose department, node and type"),
        _("Attach 📸 photos"),
        _("Enter 📐 measurements"),
        _("Add a 📝 description defect and details"),
        _("Choose the severity"),
        _("Review the summary — tap a field to ✏️ edit it"),
        Text(_("Tap"), " ", Bold(BTN_SAVE)),
        _("Wait for the 🤖 AI analysis, then submit your own verdict"),
    )
    return as_list(
        Text("🤖 ", Bold(_("Wagon Defect Registration Bot"))),
        as_list(
            Bold(_("How to register a defect:")),
            *(
                Text(keycap, " ", step)
                for keycap, step in zip(LIST_NUMBER_EMOJI, steps, strict=False)
            ),
        ),
        as_list(
            Text(Bold(BTN_OPEN_DEFECTS), " — ", _("view and update open defects.")),
            Text(
                Bold(BTN_ASK),
                " — ",
                _("ask about wagon maintenance, tolerance norms and depot documents."),
            ),
            Text(Bold(BTN_CANCEL), " — ", _("stop the current step at any time.")),
        ),
        Text(
            "💡 ",
            _("Tap the"),
            " ",
            Bold(_("Menu")),
            " ",
            _("button next to the message field to see all commands."),
        ),
        Text("📞 ", _("Questions? Send /support and the team will reply to you.")),
        sep="\n\n",
    )
