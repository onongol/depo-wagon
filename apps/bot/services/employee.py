import logging
import secrets
import string

from asgiref.sync import sync_to_async

from apps.bot.constants import RegStatus

logger = logging.getLogger(__name__)


@sync_to_async
def get_employee_by_id(employee_id: int):
    """Return active Employee by primary key (integer id)."""
    from apps.core.models import Employee

    try:
        return Employee.objects.select_related("user").get(
            id=employee_id, is_active=True
        )
    except Employee.DoesNotExist:
        return None


@sync_to_async
def get_employee_by_email(email: str):
    """Find an active Employee by email. Used in Step 1 of registration."""
    from apps.core.models import Employee

    try:
        return Employee.objects.select_related("user").get(
            email__iexact=email.strip(), is_active=True
        )
    except Employee.DoesNotExist:
        return None


@sync_to_async
def get_employee_by_telegram_id(telegram_id: int):
    """Return active Employee linked to this Telegram account, or None."""
    from apps.core.models import Employee

    try:
        return Employee.objects.select_related("user").get(
            telegram_id=telegram_id, is_active=True
        )
    except Employee.DoesNotExist:
        return None


@sync_to_async
def register_employee(employee: object, telegram_id: int):
    """
    Called after OTP is verified.

    - If Employee already has a User → just link telegram_id.
    - If Employee has no User      → create CustomUser, link everything,
                                     return generated password.

    Returns:
        (password_or_none, status)
        status: "linked" | "created"
    """
    from apps.users.models import CustomUser

    if employee.user_id:
        employee.telegram_id = telegram_id
        employee.save(update_fields=["telegram_id"])
        return None, RegStatus.LINKED

    alphabet = string.ascii_letters + string.digits
    password = "".join(secrets.choice(alphabet) for _ in range(10))

    user = CustomUser.objects.create_user(
        email=employee.email,
        password=password,
        first_name=employee.first_name,
        last_name=employee.last_name,
        is_active=True,
    )

    employee.user = user
    employee.telegram_id = telegram_id
    employee.save(update_fields=["user", "telegram_id"])

    return password, RegStatus.CREATED


@sync_to_async
def get_managers_and_engineers() -> list:
    """Return all active managers and engineers who have a linked Telegram account."""
    from apps.core.constants import EmployeeRole
    from apps.core.models import Employee

    return list(
        Employee.objects.filter(
            role__in=[EmployeeRole.MANAGER, EmployeeRole.ENGINEER],
            is_active=True,
        ).exclude(telegram_id=None)
    )


@sync_to_async
def link_employee_telegram(employee_id_input: str, telegram_id: int):
    """
    Link Telegram account to an employee by their employee_id string.

    Returns:
        (employee, "ok")         — successfully linked
        (None, "not_found")      — employee_id not found or inactive
        (None, "already_linked") — employee already linked to another account
    """
    from apps.core.models import Employee

    try:
        employee = Employee.objects.get(employee_id=employee_id_input, is_active=True)
    except Employee.DoesNotExist:
        return None, "not_found"

    if employee.telegram_id and employee.telegram_id != telegram_id:
        return None, "already_linked"

    employee.telegram_id = telegram_id
    employee.save(update_fields=["telegram_id"])
    return employee, "ok"
