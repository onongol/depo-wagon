import logging
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async
from django.utils import timezone

if TYPE_CHECKING:
    from apps.bot.user_data import DefectData
    from apps.core.models import Employee

logger = logging.getLogger(__name__)


def _load_defect(defect_id, op: str):
    """Return the defect with this id, or log a warning and return None."""
    from apps.defects.models import Defect

    defect = Defect.objects.filter(id=defect_id).first()
    if defect is None:
        logger.warning("%s: defect %s not found", op, defect_id)
    return defect


@sync_to_async
def create_defect(defect_data: DefectData, *, employee_id):
    """Create and return a new Defect record from a completed conversation."""
    from apps.defects.models import Defect

    return Defect.objects.create(
        wagon_id=defect_data.wagon_id,
        node=defect_data.node,
        defect_type=defect_data.defect_type,
        severity=defect_data.severity,
        description=defect_data.description,
        inspector_id=employee_id,
        department=defect_data.department or "",
        part_number=defect_data.part_number or "",
        responsible_employee_id=defect_data.responsible_employee_id,
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
    """Write the AI result with save() so the history and updated_at record it."""
    defect = _load_defect(defect_id, "update_defect_ai_result")

    if defect is None:
        return

    defect.ai_defect_class = ai_class
    defect.ai_confidence = ai_confidence
    defect.ai_recommendation = ai_recommendation
    defect.ai_verdict = ai_verdict

    defect.save(
        update_fields=[
            "ai_defect_class",
            "ai_confidence",
            "ai_recommendation",
            "ai_verdict",
        ]
    )


@sync_to_async
def update_defect_status(defect_id, status: str, *, employee: Employee) -> bool:
    """Save the status if this employee may change the defect; True if saved."""
    from apps.defects.models import Defect

    if employee is None:
        msg = "employee is required"
        raise ValueError(msg)

    defect = Defect.objects.status_changeable_by(employee).filter(id=defect_id).first()

    if defect is None:
        logger.warning(
            "update_defect_status: defect %s not changeable by employee %s",
            defect_id,
            employee.pk,
        )
        return False

    defect.set_status(status)
    return True


@sync_to_async
def save_employee_verdict(defect_id, verdict: str) -> None:
    defect = _load_defect(defect_id, "save_employee_verdict")

    if defect is None:
        return

    defect.verdict = verdict

    defect.save(update_fields=["verdict"])
