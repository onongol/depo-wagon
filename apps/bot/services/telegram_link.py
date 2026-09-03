import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.urls import reverse

from apps.bot.constants import LinkStatus

logger = logging.getLogger(__name__)


def get_connect_url() -> str:
    """Absolute URL of the page where an employee attaches their Telegram.

    Synchronous and cheap — it touches neither the database nor the cache — so
    handlers can call it inline without awaiting.
    """
    return f"{settings.SITE_URL.rstrip('/')}{reverse('web:telegram_connect')}"


@sync_to_async
def resolve_link_token(token: str):
    """Spend a deep-link token and return the employee it was issued for.

    The token is redeemed here, before the chat is asked to confirm, so that it
    stays single-use while the question waits for an answer.

    Returns:
        (employee, LinkStatus.OK)         — token spent, employee found
        (None, LinkStatus.INVALID_TOKEN)  — unknown, used or expired token
        (None, LinkStatus.NO_EMPLOYEE)    — user has no active Employee row
    """
    from apps.core.models import Employee
    from apps.users import telegram_tokens

    user_id = telegram_tokens.redeem(token)
    if user_id is None:
        return None, LinkStatus.INVALID_TOKEN

    try:
        employee = Employee.objects.select_related("user").get(
            user_id=user_id, is_active=True
        )
    except Employee.DoesNotExist:
        logger.warning("resolve_link_token: no active employee for user %s", user_id)
        return None, LinkStatus.NO_EMPLOYEE

    return employee, LinkStatus.OK


@sync_to_async
def attach_telegram(employee_id: int, telegram_id: int):
    """Record this chat against the employee a token resolved to.

    The employee is read again rather than carried over: whoever was
    deactivated between the question and the answer must not be attached.

    Returns:
        (employee, LinkStatus.OK)         — attached
        (None, LinkStatus.NO_EMPLOYEE)    — no active Employee row any more
        (None, LinkStatus.ALREADY_LINKED) — chat belongs to someone else
    """
    from apps.core.models import Employee

    try:
        employee = Employee.objects.select_related("user").get(
            pk=employee_id, is_active=True
        )
    except Employee.DoesNotExist:
        logger.warning("attach_telegram: employee %s is gone or inactive", employee_id)
        return None, LinkStatus.NO_EMPLOYEE

    # Refuse to move a chat that already belongs to a different employee.
    # Otherwise two people sharing a phone could silently steal each other's
    # notifications, and the previous owner would never be told. Inactive
    # holders count: telegram_id is unique across every row, active or not.
    taken_by = (
        Employee.objects.filter(telegram_id=telegram_id).exclude(pk=employee.pk).first()
    )
    if taken_by is not None:
        return None, LinkStatus.ALREADY_LINKED

    employee.telegram_id = telegram_id
    employee.save(update_fields=["telegram_id"])

    if employee.user_id:
        from apps.users.notifications import CONNECTED, notify_telegram_link_change

        notify_telegram_link_change(employee.user, CONNECTED)

    return employee, LinkStatus.OK
