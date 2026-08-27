import logging

from asgiref.sync import sync_to_async

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
def get_employee_for_auth(email: str, telegram_id: int):
    """
    Find employee by email and validate Telegram linkage.

    Returns:
        (employee, "ok")            — found, not linked to another account
        (None, "not_found")         — no active employee with this email
        (None, "already_linked")    — linked to a different Telegram account
    """
    from apps.core.models import Employee

    try:
        employee = Employee.objects.select_related("user").get(
            email__iexact=email.strip(), is_active=True
        )
    except Employee.DoesNotExist:
        return None, "not_found"

    if employee.telegram_id and employee.telegram_id != telegram_id:
        return None, "already_linked"

    return employee, "ok"


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
def get_employees_by_department(department: str) -> list:
    """Return all active employees belonging to the given department."""
    from apps.core.models import Employee

    return list(
        Employee.objects.filter(department=department, is_active=True).order_by(
            "last_name", "first_name"
        )
    )


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
