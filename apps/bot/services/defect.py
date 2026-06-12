import logging

from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)


def _load_defect(defect_id, op: str):
    """Fetch a Defect by id; log a warning and return None if it's missing.

    Sync helper — called from inside the @sync_to_async service functions.
    """
    from apps.defects.models import Defect

    defect = Defect.objects.filter(id=defect_id).first()
    if defect is None:
        logger.warning("%s: defect %s not found", op, defect_id)
    return defect


@sync_to_async
def create_defect(
    wagon_id,
    node,
    defect_type,
    severity,
    description,
    employee_id,
    department: str = "",
    part_number: str = "",
    responsible_employee_id=None,
):
    """Create and return a new Defect record."""
    from apps.defects.models import Defect

    return Defect.objects.create(
        wagon_id=wagon_id,
        node=node,
        defect_type=defect_type,
        severity=severity,
        description=description,
        inspector_id=employee_id,
        department=department,
        part_number=part_number,
        responsible_employee_id=responsible_employee_id,
        inspected_at=timezone.now(),
    )


@sync_to_async
def update_defect_ai_result(
    defect_id,
    ai_class: str,
    ai_confidence,
    ai_recommendation: str,
    ai_verdict: str,
) -> None:
    """Write AI analysis results back to the Defect record."""
    defect = _load_defect(defect_id, "update_defect_ai_result")

    if defect is None:
        return

    defect.ai_defect_class = ai_class
    defect.ai_confidence = ai_confidence
    defect.ai_recommendation = ai_recommendation
    defect.ai_verdict = ai_verdict

    # save() — not filter().update() — so auto_now (updated_at) and
    # simple_history fire. update() bypasses both and loses the audit trail.
    defect.save(
        update_fields=[
            "ai_defect_class",
            "ai_confidence",
            "ai_recommendation",
            "ai_verdict",
        ]
    )


@sync_to_async
def update_defect_status(defect_id, status: str) -> None:
    """Update the status of a Defect record. Sets repaired_at automatically when closed."""
    from apps.defects.constants import DefectStatus

    defect = _load_defect(defect_id, "update_defect_status")

    if defect is None:
        return

    defect.status = status
    fields = ["status"]

    if status == DefectStatus.CLOSED:
        defect.repaired_at = timezone.now()
        fields.append("repaired_at")

    defect.save(update_fields=fields)


@sync_to_async
def save_employee_verdict(defect_id, verdict: str) -> None:
    """Save the employee's own verdict to the Defect record."""
    defect = _load_defect(defect_id, "save_employee_verdict")

    if defect is None:
        return

    defect.verdict = verdict

    defect.save(update_fields=["verdict"])


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
