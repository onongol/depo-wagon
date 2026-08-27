import logging

from asgiref.sync import sync_to_async

from apps.bot.constants import LinkStatus

logger = logging.getLogger(__name__)


@sync_to_async
def link_telegram_by_token(token: str, telegram_id: int):
    """Attach this Telegram chat to the user a deep-link token was issued for.

    The token came from an authenticated web session, so identity is already
    established; all that is left is to record the chat against the right
    Employee.

    Returns:
        (employee, LinkStatus.OK)              — attached
        (None, LinkStatus.INVALID_TOKEN)       — unknown, used or expired token
        (None, LinkStatus.NO_EMPLOYEE)         — user has no active Employee row
        (employee, LinkStatus.ALREADY_LINKED)  — chat belongs to someone else
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
        logger.warning(
            "link_telegram_by_token: no active employee for user %s", user_id
        )
        return None, LinkStatus.NO_EMPLOYEE

    # Refuse to move a chat that already belongs to a different employee.
    # Otherwise two people sharing a phone could silently steal each other's
    # notifications, and the previous owner would never be told.
    taken_by = (
        Employee.objects.filter(telegram_id=telegram_id, is_active=True)
        .exclude(pk=employee.pk)
        .first()
    )
    if taken_by is not None:
        return None, LinkStatus.ALREADY_LINKED

    employee.telegram_id = telegram_id
    employee.save(update_fields=["telegram_id"])
    return employee, LinkStatus.OK
