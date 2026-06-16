from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="defects.Defect")
def on_defect_closed(sender, instance, **kwargs) -> None:
    """Embed a defect for historical RAG when it is closed and has a verdict."""
    from apps.defects.constants import DefectStatus

    if instance.status != DefectStatus.CLOSED:
        return

    from apps.ai_service.tasks import embed_defect_task

    embed_defect_task.delay(str(instance.id))
