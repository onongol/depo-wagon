import pytest
from django.core.files.base import ContentFile
from model_bakery import baker

from apps.ai_service.constants import DocumentStatus


@pytest.fixture
def depot_document(db):
    from apps.ai_service.models import DepotDocument

    doc = baker.make(
        DepotDocument, title="Test Document", status=DocumentStatus.PENDING
    )
    doc.file.save("test.pdf", ContentFile(b"%PDF-1.4 fake content"))
    return doc


@pytest.fixture
def ready_document(db):
    from apps.ai_service.models import DepotDocument

    doc = baker.make(DepotDocument, title="Ready Document", status=DocumentStatus.READY)
    doc.file.save("ready.pdf", ContentFile(b"%PDF-1.4 fake content"))
    return doc
