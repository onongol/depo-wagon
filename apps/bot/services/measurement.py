import logging

from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


@sync_to_async
def create_measurement(defect_id, dimension: str, value, norm_value, unit: str):
    """Create a DefectMeasurement linked to the given defect."""
    from apps.defects.models import DefectMeasurement

    return DefectMeasurement.objects.create(
        defect_id=defect_id,
        dimension=dimension,
        value=value,
        norm_value=norm_value,
        unit=unit,
    )
