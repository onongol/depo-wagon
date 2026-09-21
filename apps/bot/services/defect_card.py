from dataclasses import dataclass
from typing import TYPE_CHECKING

from asgiref.sync import sync_to_async

from apps.bot.constants import STATUS_TRANSITIONS

if TYPE_CHECKING:
    from apps.core.models import Employee
    from apps.defects.constants import DefectStatus
    from apps.defects.models import Defect, DefectMeasurement


@dataclass(frozen=True)
class DefectCard:
    """Everything the card screen renders, read once so the text layer needs no ORM."""

    defect: Defect
    measurements: tuple[DefectMeasurement, ...]
    photo_count: int
    targets: tuple[DefectStatus, ...]


def build_defect_card(defect_id, *, employee: Employee) -> DefectCard | None:
    """The defect if this employee sees it, with the statuses they may move it to.

    Sync, so a caller already holding the row in a transaction can reuse it.
    """
    from django.db.models import Count, Prefetch

    from apps.defects.models import Defect, DefectMeasurement

    if employee is None:
        msg = "employee is required"
        raise ValueError(msg)

    defect = (
        Defect.objects.visible_to_employee(employee)
        .select_related("wagon", "inspector", "responsible_employee")
        .prefetch_related(
            Prefetch(
                "measurements",
                queryset=DefectMeasurement.objects.order_by("created_at"),
            )
        )
        .annotate(photo_count=Count("photos"))
        .filter(id=defect_id)
        .first()
    )

    if defect is None:
        return None

    targets = (
        STATUS_TRANSITIONS.get(defect.status, ())
        if employee.changes_defect_statuses
        else ()
    )

    return DefectCard(
        defect=defect,
        measurements=tuple(defect.measurements.all()),
        photo_count=defect.photo_count,
        targets=targets,
    )


get_defect_card = sync_to_async(build_defect_card)
