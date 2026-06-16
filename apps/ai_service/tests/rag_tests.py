from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from asgiref.sync import sync_to_async


class TestEmbedQuery:
    async def test_returns_list_of_floats(self):
        from apps.ai_service.rag.embedding import embed_query

        vector = [0.1, 0.2, 0.3]
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=vector)]
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

        with patch(
            "apps.ai_service.rag.embedding.get_genai_client", return_value=mock_client
        ):
            result = await embed_query("bogie crack inspection")

        assert result == vector

    async def test_uses_retrieval_query_task_type(self):
        from apps.ai_service.rag.embedding import embed_query

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=[0.5])]
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

        with patch(
            "apps.ai_service.rag.embedding.get_genai_client", return_value=mock_client
        ):
            await embed_query("some query")

        call_kwargs = mock_client.aio.models.embed_content.call_args.kwargs
        assert call_kwargs["config"].task_type == "RETRIEVAL_QUERY"

    async def test_passes_text_as_contents(self):
        from apps.ai_service.rag.embedding import embed_query

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.embeddings = [MagicMock(values=[0.1])]
        mock_client.aio.models.embed_content = AsyncMock(return_value=mock_response)

        with patch(
            "apps.ai_service.rag.embedding.get_genai_client", return_value=mock_client
        ):
            await embed_query("my query text")

        call_kwargs = mock_client.aio.models.embed_content.call_args.kwargs
        assert call_kwargs["contents"] == "my query text"


class TestDescribeImages:
    async def test_returns_description_text(self):
        from apps.ai_service.rag.generation import describe_images

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Visible crack on bogie frame"
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        jpeg_bytes = b"\xff\xd8\xff" + b"\x00" * 50

        with patch(
            "apps.ai_service.rag.generation.get_genai_client", return_value=mock_client
        ):
            result = await describe_images([jpeg_bytes])

        assert result == "Visible crack on bogie frame"

    async def test_empty_response_returns_empty_string(self):
        from apps.ai_service.rag.generation import describe_images

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with patch(
            "apps.ai_service.rag.generation.get_genai_client", return_value=mock_client
        ):
            result = await describe_images([b"\xff\xd8\xff"])

        assert result == ""

    async def test_includes_all_photos_in_request(self):
        from apps.ai_service.rag.generation import describe_images

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "description"
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        photos = [b"\xff\xd8\xff" + b"\x00" * 10, b"\x89PNG" + b"\x00" * 10]

        with patch(
            "apps.ai_service.rag.generation.get_genai_client", return_value=mock_client
        ):
            await describe_images(photos)

        call_kwargs = mock_client.aio.models.generate_content.call_args.kwargs
        contents = call_kwargs["contents"]
        # 2 image parts + 1 prompt string
        assert len(contents) == 3


@pytest.mark.django_db(transaction=True)
class TestFetchSimilarChunks:
    async def test_returns_top_k_chunks_from_ready_docs(self, ready_document):
        from apps.ai_service.models import DocumentChunk
        from apps.ai_service.rag.retrieval import fetch_similar_chunks

        create = sync_to_async(DocumentChunk.objects.create)
        await create(
            document=ready_document,
            content="axle bearing wear tolerance",
            embedding=[0.1] * 1536,
            chunk_index=0,
        )
        await create(
            document=ready_document,
            content="bogie frame inspection criteria",
            embedding=[0.2] * 1536,
            chunk_index=1,
        )

        result = await fetch_similar_chunks([0.15] * 1536, top_k=5)

        assert isinstance(result, list)
        assert all(isinstance(c, str) for c in result)
        assert len(result) <= 2

    async def test_excludes_chunks_from_non_ready_documents(self, depot_document):
        from apps.ai_service.models import DocumentChunk
        from apps.ai_service.rag.retrieval import fetch_similar_chunks

        create = sync_to_async(DocumentChunk.objects.create)
        await create(
            document=depot_document,
            content="pending doc chunk",
            embedding=[0.1] * 1536,
            chunk_index=0,
        )

        result = await fetch_similar_chunks([0.1] * 1536, top_k=5)

        assert "pending doc chunk" not in result

    async def test_respects_top_k_limit(self, ready_document):
        from apps.ai_service.models import DocumentChunk
        from apps.ai_service.rag.retrieval import fetch_similar_chunks

        create = sync_to_async(DocumentChunk.objects.create)
        for i in range(10):
            await create(
                document=ready_document,
                content=f"chunk number {i}",
                embedding=[float(i) / 10] * 1536,
                chunk_index=i,
            )

        result = await fetch_similar_chunks([0.5] * 1536, top_k=3)
        assert len(result) <= 3

    async def test_returns_empty_list_when_no_documents(self):
        from apps.ai_service.rag.retrieval import fetch_similar_chunks

        result = await fetch_similar_chunks([0.1] * 1536)
        assert result == []
