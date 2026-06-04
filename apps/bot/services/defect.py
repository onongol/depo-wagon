import logging

from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


@sync_to_async
def create_defect(wagon_id, node, defect_type, severity, description, employee_id):
    """Create and return a new Defect record."""
    from apps.defects.models import Defect

    return Defect.objects.create(
        wagon_id=wagon_id,
        node=node,
        defect=defect_type,
        severity=severity,
        description=description,
        inspector_id=employee_id,
        inspected_at=timezone.now(),
    )


@sync_to_async
def update_defect_ai_result(
    defect_id,
    ai_class: str,
    ai_confidence,
    ai_rag_recommendation: str,
    ai_verdict: str,
):
    """Write AI analysis results back to the Defect record."""
    from apps.defects.models import Defect

    Defect.objects.filter(id=defect_id).update(
        ai_defect_class=ai_class,
        ai_confidence=ai_confidence,
        ai_rag_recommendation=ai_rag_recommendation,
        ai_verdict=ai_verdict,
    )


@sync_to_async
def update_defect_status(defect_id, status: str):
    """Update the status of a Defect record. Sets repaired_at automatically when closed."""
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    fields = {"status": status}
    if status == DefectStatus.CLOSED:
        fields["repaired_at"] = timezone.now()

    Defect.objects.filter(id=defect_id).update(**fields)


@sync_to_async
def save_employee_verdict(defect_id, verdict: str):
    """Save the employee's own verdict to the Defect record."""
    from apps.defects.models import Defect

    Defect.objects.filter(id=defect_id).update(verdict=verdict)


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
    """Return total count of open/in-progress defects. Filtered by employee if provided."""
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect

    qs = Defect.objects.filter(status__in=[DefectStatus.OPEN, DefectStatus.IN_PROGRESS])
    if employee_id is not None:
        qs = qs.filter(inspector_id=employee_id)

    return qs.count()
