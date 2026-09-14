from asgiref.sync import sync_to_async


@sync_to_async
def create_measurements_bulk(defect_id, measurements: list) -> None:
    """Bulk-insert DefectMeasurement records for the given defect."""
    from apps.defects.models import DefectMeasurement

    DefectMeasurement.objects.bulk_create(
        [
            DefectMeasurement(
                defect_id=defect_id,
                dimension=measurement.dimension,
                value=measurement.value,
                norm_value=measurement.norm_value,
                unit=measurement.unit,
            )
            for measurement in measurements
        ]
    )
