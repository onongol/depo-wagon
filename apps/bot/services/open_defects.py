from asgiref.sync import sync_to_async


def _open_defects():
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    return Defect.objects.filter(
        status__in=[DefectStatus.OPEN, DefectStatus.IN_PROGRESS]
    )


def _own_open_defects(employee_id: int):
    if employee_id is None:
        msg = "employee_id is required"
        raise ValueError(msg)
    return _open_defects().filter(inspector_id=employee_id)


def _page(qs, limit: int, offset: int) -> list:
    qs = qs.select_related("wagon", "inspector").order_by("-inspected_at")
    return list(qs[offset : offset + limit])


@sync_to_async
def get_open_defects(*, employee_id: int, limit: int = 5, offset: int = 0) -> list:
    """Return one page of this employee's open and in-progress defects."""
    return _page(_own_open_defects(employee_id), limit, offset)


@sync_to_async
def get_open_defects_count(*, employee_id: int) -> int:
    """Count this employee's open and in-progress defects."""
    return _own_open_defects(employee_id).count()


@sync_to_async
def get_all_open_defects(*, limit: int = 5, offset: int = 0) -> list:
    """Return one page of every employee's open defects. Check the role first."""
    return _page(_open_defects(), limit, offset)


@sync_to_async
def get_all_open_defects_count() -> int:
    """Count every employee's open defects. Check the role first."""
    return _open_defects().count()
