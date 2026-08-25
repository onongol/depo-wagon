from asgiref.sync import sync_to_async


@sync_to_async
def create_photo_from_bytes(defect_id, file_bytes: bytes, filename: str):
    """
    Save photo bytes to default storage (Cloudflare R2 in production)
    and create a DefectPhoto record.
    """
    from django.core.files.base import ContentFile

    from apps.defects.models import DefectPhoto

    photo = DefectPhoto(defect_id=defect_id)
    photo.image.save(filename, ContentFile(file_bytes), save=True)
    return photo
