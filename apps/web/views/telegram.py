from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.users import telegram_tokens
from apps.users.notifications import DISCONNECTED, notify_telegram_link_change
from apps.web.decorators import employee_required


@employee_required
def telegram_connect(request):
    """Show whether this employee's Telegram is attached, and offer to attach it.

    The deep link is built here, from an authenticated session, which is what
    makes the bot side trivial: by the time the token reaches the bot, who it
    belongs to is already settled. The bot never has to establish identity of
    its own.
    """
    employee = request.user.employee
    context = {
        "employee": employee,
        "is_linked": employee.telegram_id is not None,
        "bot_username": settings.TELEGRAM_BOT_USERNAME,
    }

    if not context["is_linked"] and settings.TELEGRAM_BOT_USERNAME:
        token = telegram_tokens.issue(request.user.pk)
        context["deep_link"] = (
            f"https://t.me/{settings.TELEGRAM_BOT_USERNAME}?start={token}"
        )

    return render(request, "web/telegram/connect.html", context)


@require_POST
@employee_required
def telegram_disconnect(request):
    """Detach the Telegram account from this employee.

    POST only: detaching is a state change, and a GET would let any page do it
    to a signed-in employee with nothing more than an image tag.
    """
    employee = request.user.employee
    employee.telegram_id = None
    employee.save(update_fields=["telegram_id"])
    notify_telegram_link_change(request.user, DISCONNECTED)
    messages.success(request, _("Telegram account disconnected."))
    return redirect("web:telegram_connect")
