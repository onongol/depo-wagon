import logging

from allauth.account.utils import perform_login
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET

from apps.users import login_tokens

logger = logging.getLogger(__name__)


@require_GET
def login_link(request, token: str):
    """Sign in the browser that followed a one-time link from the Telegram bot.

    Login goes through allauth's ``perform_login`` rather than Django's
    ``login()`` so this path behaves like every other way into the app: it runs
    allauth's login stages, which is what applies two-factor authentication when
    the account has it enabled. Calling Django's ``login()`` directly would sign
    the person straight in and quietly skip that check.
    """
    user_id = login_tokens.redeem(token)
    if user_id is None:
        messages.error(
            request,
            _(
                "This sign-in link has expired or has already been used. Open the bot and request a new one."
            ),
        )
        return redirect("account_login")

    try:
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except get_user_model().DoesNotExist:
        # The token outlived the account, or the person was deactivated between
        # the link being issued and followed.
        logger.warning("login_link: no active user for redeemed token, id=%s", user_id)
        messages.error(request, _("This account is no longer active."))
        return redirect("account_login")

    # No email_verification override: the default still applies, so a link can
    # never be a way around verification. Accounts the bot issues links for are
    # already marked verified when it creates them.
    return perform_login(request, user)
