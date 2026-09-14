from asgiref.sync import sync_to_async

from .employee import load_active_employee


def _visible_open_defects(employee_id: int):
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    employee = load_active_employee(employee_id)
    if employee is None:
        return Defect.objects.none()
    return Defect.objects.visible_to_employee(employee).filter(
        status__in=[DefectStatus.OPEN, DefectStatus.IN_PROGRESS]
    )


def _page(qs, limit: int, offset: int) -> list:
    qs = qs.select_related("wagon", "inspector").order_by("-inspected_at")
    return list(qs[offset : offset + limit])


@sync_to_async
def get_open_defects(*, employee_id: int, limit: int = 5, offset: int = 0) -> list:
    """Return one page of the open and in-progress defects this employee sees."""
    return _page(_visible_open_defects(employee_id), limit, offset)


@sync_to_async
def get_open_defects_count(*, employee_id: int) -> int:
    """Count the open and in-progress defects this employee sees."""
    return _visible_open_defects(employee_id).count()
