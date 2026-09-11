from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    from apps.core.models import Employee


@sync_to_async
def get_employee_by_telegram_id(telegram_id: int) -> Employee | None:
    """Return active Employee linked to this Telegram account, or None."""
    from apps.core.models import Employee

    try:
        return Employee.objects.get(telegram_id=telegram_id, is_active=True)
    except Employee.DoesNotExist:
        return None


@sync_to_async
def get_employees_by_department(department: str) -> list[Employee]:
    """Return all active employees belonging to the given department."""
    from apps.core.models import Employee

    return list(
        Employee.objects.filter(department=department, is_active=True).order_by(
            "last_name", "first_name"
        )
    )


@sync_to_async
def get_managers_and_engineers() -> list[Employee]:
    """Return all active managers and engineers who have a linked Telegram account."""
    from apps.core.constants import EmployeeRole
    from apps.core.models import Employee

    return list(
        Employee.objects.filter(
            role__in=[EmployeeRole.MANAGER, EmployeeRole.ENGINEER],
            is_active=True,
        ).exclude(telegram_id=None)
    )
