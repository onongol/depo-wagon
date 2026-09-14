from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

if TYPE_CHECKING:
    from apps.core.models import Employee


def _visible_open_defects(employee: Employee):
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    if employee is None:
        msg = "employee is required"
        raise ValueError(msg)
    return Defect.objects.visible_to_employee(employee).filter(
        status__in=[DefectStatus.OPEN, DefectStatus.IN_PROGRESS]
    )


def _page(qs, limit: int, offset: int) -> list:
    qs = qs.select_related("wagon", "inspector").order_by("-inspected_at")
    return list(qs[offset : offset + limit])


@sync_to_async
def get_open_defects(*, employee: Employee, limit: int = 5, offset: int = 0) -> list:
    """Return one page of the open and in-progress defects this employee sees."""
    return _page(_visible_open_defects(employee), limit, offset)


@sync_to_async
def get_open_defects_count(*, employee: Employee) -> int:
    """Count the open and in-progress defects this employee sees."""
    return _visible_open_defects(employee).count()
