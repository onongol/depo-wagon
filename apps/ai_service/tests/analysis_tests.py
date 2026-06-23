from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.defects.constants import DefectVerdict

_CHUNK = {"content": "chunk content", "document__title": "Test Manual", "page_number": 1}
_CHUNK_NO_PAGE = {"content": "chunk content", "document__title": "Test Manual", "page_number": None}
_DEFECT_CASE = {"content": "Past bogie crack — verdict: repair_now", "created_at": datetime(2024, 11, 1, tzinfo=timezone.utc)}


def _schema_json(
    defect_class="Bogie frame crack",
    confidence=0.87,
    verdict=DefectVerdict.REPAIR_NOW,
    rag_recommendation="Immediate repair required.",
):
    from apps.ai_service.analysis.schema import FullAnalysisSchema

    return FullAnalysisSchema(
        defect_class=defect_class,
        confidence=confidence,
        verdict=verdict,
        rag_recommendation=rag_recommendation,
    ).model_dump_json()


def _make_mock_client(response_text):
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return mock_client


class TestAnalyzeDefect:
    async def test_returns_populated_ai_result(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[_CHUNK])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            result = await analyze_defect(node="Bogie", defect_type="Crack", severity="Critical")

        assert result.defect_class == "Bogie frame crack"
        assert result.confidence == pytest.approx(0.87)
        assert result.verdict == DefectVerdict.REPAIR_NOW
        assert result.rag_recommendation == "Immediate repair required."

    async def test_sources_populated_from_chunks_and_defects(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[_CHUNK])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[_DEFECT_CASE])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            result = await analyze_defect(node="A", defect_type="B", severity="C")

        assert any("Test Manual" in s for s in result.sources)
        assert any("🔁 1 precedent cases" in s for s in result.sources)

    async def test_returns_empty_result_on_embedding_failure(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=MagicMock()),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(side_effect=RuntimeError("API down"))),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            result = await analyze_defect(node="X", defect_type="Y", severity="Z")

        assert result.defect_class == ""
        assert result.confidence is None

    async def test_proceeds_without_rag_when_vector_search_fails(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json(defect_class="Wear"))

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(side_effect=RuntimeError("DB down"))),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            result = await analyze_defect(node="A", defect_type="B", severity="C")

        assert result.defect_class == "Wear"
        call_args = client.aio.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args.args[0]
        prompt_text = next(c for c in reversed(contents) if isinstance(c, str))
        assert "No depot documents found" in prompt_text

    async def test_returns_empty_result_on_empty_gemini_response(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(None)

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            result = await analyze_defect(node="A", defect_type="B", severity="C")

        assert result.defect_class == ""

    async def test_description_included_in_prompt(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)) as mock_embed,
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            await analyze_defect(node="Wheelset", defect_type="Wear", severity="Medium", description="Crack on the rim")

        query_text = mock_embed.call_args.args[0]
        assert "Crack on the rim" in query_text

    async def test_rag_context_included_in_prompt(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())
        chunk = {"content": "Relevant depot rule", "document__title": "Depot Manual", "page_number": 5}

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[chunk])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            await analyze_defect(node="A", defect_type="B", severity="C")

        call_args = client.aio.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args.args[0]
        prompt_text = next(c for c in reversed(contents) if isinstance(c, str))
        assert "Relevant depot rule" in prompt_text
        assert "Depot Manual" in prompt_text

    async def test_defect_history_included_in_prompt(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[_DEFECT_CASE])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            await analyze_defect(node="A", defect_type="B", severity="C")

        call_args = client.aio.models.generate_content.call_args
        contents = call_args.kwargs.get("contents") or call_args.args[0]
        prompt_text = next(c for c in reversed(contents) if isinstance(c, str))
        assert "Past bogie crack" in prompt_text
        assert "Similar cases from depot history" in prompt_text

    async def test_photos_trigger_image_description(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())
        jpeg = b"\xff\xd8\xff" + b"\x00" * 50

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="Crack visible")) as mock_desc,
        ):
            await analyze_defect(node="A", defect_type="B", severity="C", photos_bytes=[jpeg])

        mock_desc.assert_called_once_with([jpeg])

    async def test_image_description_failure_does_not_abort(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = _make_mock_client(_schema_json())
        jpeg = b"\xff\xd8\xff" + b"\x00" * 50

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(side_effect=RuntimeError("Vision API down"))),
        ):
            result = await analyze_defect(node="A", defect_type="B", severity="C", photos_bytes=[jpeg])

        assert result.defect_class == "Bogie frame crack"

    async def test_unhandled_exception_returns_empty_result(self):
        from apps.ai_service.analysis.pipeline import analyze_defect

        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(side_effect=ValueError("Unexpected"))

        with (
            patch("apps.ai_service.analysis.pipeline.get_genai_client", return_value=client),
            patch("apps.ai_service.analysis.pipeline.embed_query", new=AsyncMock(return_value=[0.1] * 1536)),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_chunks", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.fetch_similar_defects", new=AsyncMock(return_value=[])),
            patch("apps.ai_service.analysis.pipeline.describe_images", new=AsyncMock(return_value="")),
        ):
            result = await analyze_defect(node="A", defect_type="B", severity="C")

        assert result.defect_class == ""
