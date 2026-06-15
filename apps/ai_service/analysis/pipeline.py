import logging

from google.genai import types

from apps.ai_service.analysis.config import ANALYSIS_PROMPT
from apps.ai_service.analysis.schema import FullAnalysisSchema
from apps.ai_service.client import get_genai_client
from apps.ai_service.config import GENERATION_MODEL
from apps.ai_service.rag.embedding import embed_query
from apps.ai_service.rag.generation import describe_images
from apps.ai_service.rag.retrieval import fetch_similar_chunks
from apps.ai_service.utils import mime_type_for_bytes
from apps.bot.user_data import AIResult

logger = logging.getLogger(__name__)


async def analyze_defect(
    node: str,
    defect_type: str,
    severity: str,
    description: str = "",
    photos_bytes: list[bytes] | None = None,
) -> AIResult:
    """
    Unified pipeline — single Gemini call returns structured fields + RAG recommendation:
      1. Describe photos → augment query text
      2. Embed query with gemini-embedding-2
      3. Vector search → top-K depot document chunks
      4. Build prompt with retrieved context
      5. Single gemini-3.5-flash call with structured schema
    """
    try:
        client = get_genai_client()

        # Build query text
        query_parts = [
            f"Узел/Элемент: {node}",
            f"Тип дефекта: {defect_type}",
            f"Степень критичности: {severity}",
        ]
        if description:
            query_parts.append(f"Описание: {description}")

        if photos_bytes:
            try:
                visual_desc = await describe_images(photos_bytes)
                if visual_desc:
                    query_parts.append(f"Визуальные признаки: {visual_desc}")
            except Exception as exc:
                logger.warning("Image description failed: %s", exc)

        query_text = "\n".join(query_parts)

        # Embed query
        try:
            query_embedding = await embed_query(query_text)
        except Exception as exc:
            logger.warning("Embedding failed, skipping AI analysis: %s", exc)
            return AIResult()

        # Vector search
        try:
            chunks = await fetch_similar_chunks(query_embedding)
        except Exception as exc:
            logger.warning(
                "Vector search failed, proceeding without RAG context: %s", exc
            )
            chunks = []

        # Build RAG context
        if chunks:
            context_block = "\n\n---\n\n".join(chunks)
            rag_context = (
                "=== Справочные материалы из документов депо ===\n\n"
                f"{context_block}\n\n"
                "=== Конец справочных материалов ==="
            )
        else:
            rag_context = (
                "(Документы депо не найдены — используй общие технические знания.)"
            )

        description_line = (
            f"<user_description>\n{description}\n</user_description>"
            if description
            else ""
        )

        prompt = ANALYSIS_PROMPT.format(
            node=node,
            defect_type=defect_type,
            severity=severity,
            description_line=description_line,
            rag_context=rag_context,
        )

        # Single structured call with photos
        contents: list = []
        for photo in photos_bytes or []:
            contents.append(
                types.Part.from_bytes(data=photo, mime_type=mime_type_for_bytes(photo))
            )
        contents.append(prompt)

        response = await client.aio.models.generate_content(
            model=GENERATION_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=FullAnalysisSchema,
                temperature=0.1,
                max_output_tokens=2048,
            ),
        )

        if not response.text:
            logger.warning("Gemini returned empty response")
            return AIResult()

        result = FullAnalysisSchema.model_validate_json(response.text)

        return AIResult(
            defect_class=result.defect_class,
            confidence=result.confidence,
            rag_recommendation=result.rag_recommendation,
            verdict=result.verdict,
        )

    except Exception as exc:
        logger.error("AI analysis failed: %s", exc, exc_info=True)
        return AIResult()
