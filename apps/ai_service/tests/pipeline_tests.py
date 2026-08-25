from unittest.mock import patch

import pytest

from apps.ai_service.constants import DocumentStatus


@pytest.mark.django_db
class TestProcessDocument:
    def test_nonexistent_document_returns_early(self):
        from apps.ai_service.processing.pipeline import process_document

        process_document(99999)  # Must not raise

    def test_status_becomes_ready_on_success(self, depot_document):
        from apps.ai_service.processing.pipeline import process_document

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract, \
                patch("apps.ai_service.processing.pipeline.chunk_page") as mock_chunk, \
                patch("apps.ai_service.processing.pipeline.embed_texts") as mock_embed:
            mock_extract.return_value = [(1, "Page text")]
            mock_chunk.return_value = [{"content": "chunk text", "page_number": 1}]
            mock_embed.return_value = [[0.1] * 1536]

            process_document(depot_document.pk)

        depot_document.refresh_from_db()
        assert depot_document.status == DocumentStatus.READY
        assert depot_document.error_message == ""

    def test_chunks_are_created_in_db(self, depot_document):
        from apps.ai_service.models import DocumentChunk
        from apps.ai_service.processing.pipeline import process_document

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract, \
                patch("apps.ai_service.processing.pipeline.chunk_page") as mock_chunk, \
                patch("apps.ai_service.processing.pipeline.embed_texts") as mock_embed:
            mock_extract.return_value = [(1, "text"), (2, "more text")]
            mock_chunk.side_effect = [
                [{"content": "chunk 1", "page_number": 1}],
                [{"content": "chunk 2", "page_number": 2}],
            ]
            mock_embed.return_value = [[0.1] * 1536, [0.2] * 1536]

            process_document(depot_document.pk)

        assert DocumentChunk.objects.filter(document=depot_document).count() == 2

    def test_old_chunks_replaced_on_reprocess(self, depot_document):
        from apps.ai_service.models import DocumentChunk
        from apps.ai_service.processing.pipeline import process_document

        DocumentChunk.objects.create(
            document=depot_document,
            content="stale chunk",
            embedding=[0.0] * 1536,
            chunk_index=0,
        )

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract, \
                patch("apps.ai_service.processing.pipeline.chunk_page") as mock_chunk, \
                patch("apps.ai_service.processing.pipeline.embed_texts") as mock_embed:
            mock_extract.return_value = [(1, "new text")]
            mock_chunk.return_value = [{"content": "fresh chunk", "page_number": 1}]
            mock_embed.return_value = [[0.5] * 1536]

            process_document(depot_document.pk)

        chunks = list(depot_document.chunks.all())
        assert len(chunks) == 1
        assert chunks[0].content == "fresh chunk"

    def test_status_becomes_error_on_extraction_failure(self, depot_document):
        from apps.ai_service.processing.pipeline import process_document

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract:
            mock_extract.side_effect = RuntimeError("Corrupt PDF")
            with pytest.raises(RuntimeError, match="Corrupt PDF"):
                process_document(depot_document.pk)

        depot_document.refresh_from_db()
        assert depot_document.status == DocumentStatus.ERROR
        assert "Corrupt PDF" in depot_document.error_message

    def test_status_becomes_error_when_no_text_extracted(self, depot_document):
        from apps.ai_service.processing.pipeline import process_document

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract:
            mock_extract.return_value = []
            with pytest.raises(ValueError, match="No readable text"):
                process_document(depot_document.pk)

        depot_document.refresh_from_db()
        assert depot_document.status == DocumentStatus.ERROR

    def test_status_becomes_error_when_no_chunks_produced(self, depot_document):
        from apps.ai_service.processing.pipeline import process_document

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract, \
                patch("apps.ai_service.processing.pipeline.chunk_page") as mock_chunk:
            mock_extract.return_value = [(1, "some text")]
            mock_chunk.return_value = []
            with pytest.raises(ValueError, match="no chunks"):
                process_document(depot_document.pk)

        depot_document.refresh_from_db()
        assert depot_document.status == DocumentStatus.ERROR

    def test_error_message_cleared_on_retry_success(self, depot_document):
        from apps.ai_service.processing.pipeline import process_document

        depot_document.status = DocumentStatus.ERROR
        depot_document.error_message = "Previous failure"
        depot_document.save()

        with patch("apps.ai_service.processing.pipeline.extract_pages") as mock_extract, \
                patch("apps.ai_service.processing.pipeline.chunk_page") as mock_chunk, \
                patch("apps.ai_service.processing.pipeline.embed_texts") as mock_embed:
            mock_extract.return_value = [(1, "text")]
            mock_chunk.return_value = [{"content": "chunk", "page_number": 1}]
            mock_embed.return_value = [[0.1] * 1536]

            process_document(depot_document.pk)

        depot_document.refresh_from_db()
        assert depot_document.status == DocumentStatus.READY
        assert depot_document.error_message == ""
