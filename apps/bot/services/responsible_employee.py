from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from django.db.models import Value
from django.db.models.functions import Concat

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.core.models import Employee


def _department_employees(
    department: str | None, search: str = ""
) -> QuerySet[Employee]:
    """Active department employees whose "first last" contains search; none if unset."""
    from apps.core.models import Employee

    if not department:
        return Employee.objects.none()

    employees = Employee.objects.filter(department=department, is_active=True)
    if search:
        employees = employees.alias(
            name=Concat("first_name", Value(" "), "last_name")
        ).filter(name__icontains=search)
    return employees


@sync_to_async
def count_department_employees(department: str | None, search: str = "") -> int:
    """Count a department's active employees whose name contains search."""
    return _department_employees(department, search).count()


@sync_to_async
def get_department_employees(
    department: str | None, search: str = "", *, limit: int, offset: int = 0
) -> list[Employee]:
    """Return one page of a department's active employees, ordered by name."""
    employees = _department_employees(department, search).order_by(
        "last_name", "first_name", "pk"
    )
    return list(employees[offset : offset + limit])


@sync_to_async
def get_department_employee(
    employee_id: int, department: str | None
) -> Employee | None:
    """Return this employee while they are still active in the department."""
    return _department_employees(department).filter(pk=employee_id).first()
