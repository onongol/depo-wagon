from aiogram.utils.formatting import Bold, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _


def build_ai_chat_greeting_text() -> Text:
    return as_list(
        Text("🤖 ", Bold(_("AI Depot Assistant"))),
        Text(
            _(
                "I can answer questions about wagon maintenance, "
                "tolerance norms and depot documents."
            )
        ),
        as_list(Text(_("Type your question.")), Italic(_("To exit, type /cancel."))),
        sep="\n\n",
    )
