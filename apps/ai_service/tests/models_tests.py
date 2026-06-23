import pytest
from model_bakery import baker

from apps.ai_service.constants import DocumentStatus


@pytest.mark.django_db
class TestDepotDocument:
    def test_str_returns_title(self):
        from apps.ai_service.models import DepotDocument

        doc = baker.make(DepotDocument, title="Wagon Frame Manual")
        assert str(doc) == "Wagon Frame Manual"

    def test_default_status_is_pending(self):
        from apps.ai_service.models import DepotDocument

        doc = baker.make(DepotDocument)
        assert doc.status == DocumentStatus.PENDING

    def test_error_message_blank_by_default(self):
        from apps.ai_service.models import DepotDocument

        doc = baker.make(DepotDocument)
        assert doc.error_message == ""

    def test_description_blank_by_default(self):
        from apps.ai_service.models import DepotDocument

        doc = baker.make(DepotDocument)
        assert doc.description == ""

    def test_ordering_newest_first(self):
        from apps.ai_service.models import DepotDocument

        first = baker.make(DepotDocument, title="First")
        second = baker.make(DepotDocument, title="Second")
        docs = list(DepotDocument.objects.filter(pk__in=[first.pk, second.pk]))
        assert docs[0].pk == second.pk

    def test_status_transitions(self):
        from apps.ai_service.models import DepotDocument

        doc = baker.make(DepotDocument, status=DocumentStatus.PENDING)
        doc.status = DocumentStatus.PROCESSING
        doc.save()
        doc.refresh_from_db()
        assert doc.status == DocumentStatus.PROCESSING

        doc.status = DocumentStatus.READY
        doc.save()
        doc.refresh_from_db()
        assert doc.status == DocumentStatus.READY


@pytest.mark.django_db
class TestDocumentChunk:
    def test_str_format(self):
        from apps.ai_service.models import DepotDocument, DocumentChunk

        doc = baker.make(DepotDocument, title="Bogies Reference")
        chunk = DocumentChunk.objects.create(
            document=doc,
            content="Bogie frame inspection procedure",
            embedding=[0.1] * 1536,
            chunk_index=3,
        )
        assert str(chunk) == "Bogies Reference – 3"

    def test_cascade_delete_with_document(self):
        from apps.ai_service.models import DepotDocument, DocumentChunk

        doc = baker.make(DepotDocument, title="Temp Doc")
        DocumentChunk.objects.create(
            document=doc,
            content="some chunk",
            embedding=[0.0] * 1536,
            chunk_index=0,
        )
        doc_pk = doc.pk
        doc.delete()
        assert DocumentChunk.objects.filter(document_id=doc_pk).count() == 0

    def test_ordering_by_chunk_index(self):
        from apps.ai_service.models import DepotDocument, DocumentChunk

        doc = baker.make(DepotDocument)
        DocumentChunk.objects.create(
            document=doc, content="c", embedding=[0.0] * 1536, chunk_index=2
        )
        DocumentChunk.objects.create(
            document=doc, content="a", embedding=[0.0] * 1536, chunk_index=0
        )
        DocumentChunk.objects.create(
            document=doc, content="b", embedding=[0.0] * 1536, chunk_index=1
        )
        indices = list(doc.chunks.values_list("chunk_index", flat=True))
        assert indices == [0, 1, 2]

    def test_page_number_is_optional(self):
        from apps.ai_service.models import DepotDocument, DocumentChunk

        doc = baker.make(DepotDocument)
        chunk = DocumentChunk.objects.create(
            document=doc,
            content="chunk without page",
            embedding=[0.0] * 1536,
            chunk_index=0,
            page_number=None,
        )
        assert chunk.page_number is None


@pytest.mark.django_db
class TestDefectVector:
    def _make_defect(self):
        return baker.make("defects.Defect", wagon__manufacture_year=2020)

    def test_str_includes_defect_id(self):
        from apps.ai_service.models import DefectVector

        defect = self._make_defect()
        vec = DefectVector.objects.create(
            defect=defect,
            content="Defect: rim crack",
            embedding=[0.1] * 1536,
        )
        assert str(vec) == f"Vector({defect.pk})"

    def test_cascade_delete_with_defect(self):
        from apps.ai_service.models import DefectVector

        defect = self._make_defect()
        DefectVector.objects.create(
            defect=defect,
            content="some defect content",
            embedding=[0.0] * 1536,
        )
        defect_pk = defect.pk
        defect.delete()
        assert DefectVector.objects.filter(defect_id=defect_pk).count() == 0

    def test_one_to_one_prevents_duplicate(self):
        from django.db import IntegrityError

        from apps.ai_service.models import DefectVector

        defect = self._make_defect()
        DefectVector.objects.create(
            defect=defect,
            content="first embedding",
            embedding=[0.1] * 1536,
        )
        with pytest.raises(IntegrityError):
            DefectVector.objects.create(
                defect=defect,
                content="second embedding",
                embedding=[0.2] * 1536,
            )

    def test_created_at_set_automatically(self):
        from apps.ai_service.models import DefectVector

        defect = self._make_defect()
        vec = DefectVector.objects.create(
            defect=defect,
            content="content",
            embedding=[0.0] * 1536,
        )
        assert vec.created_at is not None

    def test_update_or_create_replaces_embedding(self):
        from apps.ai_service.models import DefectVector

        defect = self._make_defect()
        DefectVector.objects.create(
            defect=defect,
            content="old content",
            embedding=[0.1] * 1536,
        )
        DefectVector.objects.update_or_create(
            defect_id=defect.pk,
            defaults={"content": "new content", "embedding": [0.9] * 1536},
        )
        vec = DefectVector.objects.get(defect=defect)
        assert vec.content == "new content"
        assert DefectVector.objects.filter(defect=defect).count() == 1
