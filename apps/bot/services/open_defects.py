from asgiref.sync import sync_to_async


@sync_to_async
def get_open_defects(
    limit: int = 5, offset: int = 0, employee_id: int | None = None
) -> list:
    """Return open/in-progress defects. Filtered by employee if provided."""
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    qs = Defect.objects.select_related("wagon", "inspector").filter(
        status__in=[DefectStatus.OPEN, DefectStatus.IN_PROGRESS]
    )

    if employee_id is not None:
        qs = qs.filter(inspector_id=employee_id)

    return list(qs.order_by("-inspected_at")[offset : offset + limit])


@sync_to_async
def get_open_defects_count(employee_id: int | None = None) -> int:
    """Count open and in-progress defects, optionally for one employee."""
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    qs = Defect.objects.filter(status__in=[DefectStatus.OPEN, DefectStatus.IN_PROGRESS])

    if employee_id is not None:
        qs = qs.filter(inspector_id=employee_id)

    return qs.count()
