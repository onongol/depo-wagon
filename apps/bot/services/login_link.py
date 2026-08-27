from asgiref.sync import sync_to_async
from django.conf import settings
from django.urls import reverse

from apps.users import login_tokens


def get_connect_url() -> str:
    """Absolute URL of the page where an employee attaches their Telegram.

    Synchronous and cheap — it touches neither the database nor the cache — so
    handlers can call it inline without awaiting.
    """
    return f"{settings.SITE_URL.rstrip('/')}{reverse('web:telegram_connect')}"


@sync_to_async
def build_login_link(user_id: int) -> str:
    """Return an absolute, single-use URL that signs this user into the web app.

    The host comes from ``SITE_URL`` rather than from a request, because the
    only caller is the bot and there is no request in a Telegram update.
    """
    token = login_tokens.issue(user_id)
    path = reverse("login_link", kwargs={"token": token})
    return f"{settings.SITE_URL.rstrip('/')}{path}"
