from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from aiogram.types import User

    from apps.core.models import Employee


def build_support_ask_text() -> Text:
    return as_list(
        Text("✍️ ", _("Write your question and I'll forward it to the support team.")),
        Italic(_("To exit, type /cancel.")),
    )


def build_support_unavailable_text() -> Text:
    return Text(
        "⚠️ ",
        _("Support is unavailable right now. Please contact @Erdenebayaraa directly."),
    )


def build_support_sent_text() -> Text:
    return Text(
        "✅ ",
        _("Your question has been sent. The support team will reply here in the bot."),
    )


def _identity(user: User, employee: Employee | None) -> str:
    if employee is None:
        return user.full_name or user.first_name
    return (
        f"{employee.full_name} ({employee.employee_id}, {employee.get_role_display()})"
    )


def build_support_request_text(
    question: str, user: User, employee: Employee | None
) -> Text:
    return as_list(
        Text("🆘 ", Bold(_("Support request"))),
        as_list(
            Text("👤 ", _("From:"), " ", _identity(user, employee)),
            Text("💬 ", f"@{user.username}" if user.username else "—"),
        ),
        as_list(Bold(_("Question:")), question),
        Italic("↩️ ", _("Reply to this message to answer the user.")),
        sep="\n\n",
    )
