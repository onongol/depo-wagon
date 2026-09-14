from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    from apps.core.models import Employee


def load_active_employee(employee_id: int) -> Employee | None:
    """Return the active Employee with this id, or None; None as the id raises.

    Sync helper — called from inside the @sync_to_async service functions.
    """
    from apps.core.models import Employee

    if employee_id is None:
        msg = "employee_id is required"
        raise ValueError(msg)
    return Employee.objects.filter(id=employee_id, is_active=True).first()


@sync_to_async
def get_employee_by_telegram_id(telegram_id: int) -> Employee | None:
    """Return active Employee linked to this Telegram account, or None."""
    from apps.core.models import Employee

    try:
        return Employee.objects.get(telegram_id=telegram_id, is_active=True)
    except Employee.DoesNotExist:
        return None


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
