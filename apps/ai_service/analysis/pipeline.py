import asyncio
import logging

from google.genai import types

from apps.ai_service.analysis.config import ANALYSIS_PROMPT
from apps.ai_service.analysis.schema import FullAnalysisSchema
from apps.ai_service.client import get_genai_client
from apps.ai_service.config import GENERATION_MODEL
from apps.ai_service.rag.config import RAG_SYSTEM_PROMPT
from apps.ai_service.rag.embedding import embed_query
from apps.ai_service.rag.generation import describe_images
from apps.ai_service.rag.retrieval import fetch_similar_chunks, fetch_similar_defects
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
      3. Parallel vector search: docs + defect history
      4. Build prompt with tagged context blocks
      5. Single gemini-flash call with structured schema
    """
    try:
        client = get_genai_client()

        # Build query text
        query_parts = [
            f"Node/Element: {node}",
            f"Defect type: {defect_type}",
            f"Severity: {severity}",
        ]
        if description:
            query_parts.append(f"Description: {description}")

        if photos_bytes:
            try:
                visual_desc = await describe_images(photos_bytes)
                if visual_desc:
                    query_parts.append(f"Visual signs: {visual_desc}")
            except Exception as exc:
                logger.warning("Image description failed: %s", exc, exc_info=True)

        query_text = "\n".join(query_parts)

        # Embed query
        try:
            query_embedding = await embed_query(query_text)
        except Exception as exc:
            logger.warning(
                "Embedding failed, skipping AI analysis: %s", exc, exc_info=True
            )
            return AIResult()

        # Parallel vector search: regulatory docs + defect history
        try:
            chunks, past_defects = await asyncio.gather(
                fetch_similar_chunks(query_embedding, query_text),
                fetch_similar_defects(query_embedding, query_text),
            )
        except Exception as exc:
            logger.warning(
                "Vector search failed, proceeding without RAG context: %s",
                exc,
                exc_info=True,
            )
            chunks, past_defects = [], []

        # Build Doc context block with source labels
        doc_sources: list[str] = []
        if chunks:
            context_parts = []
            pages_by_title: dict[str, list[int]] = {}
            for i, chunk in enumerate(chunks, 1):
                label = f"[DOC-{i}]"
                title = chunk["document__title"]
                page = chunk.get("page_number")
                if page:
                    pages_by_title.setdefault(title, []).append(page)
                else:
                    pages_by_title.setdefault(title, [])
                source = f"{title}, p. {page}" if page else title
                context_parts.append(f"{label} {source}:\n{chunk['content']}")
            for title, pages in pages_by_title.items():
                if pages:
                    doc_sources.append(
                        f"📄 {title}, p. {', '.join(str(p) for p in sorted(set(pages)))}"
                    )
                else:
                    doc_sources.append(f"📄 {title}")
            rag_context = (
                "=== Reference materials from depot documents ===\n\n"
                + "\n\n---\n\n".join(context_parts)
                + "\n\n=== End of reference materials ==="
            )
        else:
            rag_context = (
                "(No depot documents found — use general technical knowledge.)"
            )

        # Build defect history context block with source labels
        case_sources: list[str] = []
        if past_defects:
            history_parts = []
            for i, defect in enumerate(past_defects, 1):
                label = f"[CASE-{i}]"
                date = defect["created_at"].strftime("%m.%Y")
                history_parts.append(f"{label} {date}:\n{defect['content']}")
            case_sources.append(f"🔁 {len(past_defects)} precedent cases")
            history_context = (
                "=== Similar cases from depot history ===\n\n"
                + "\n\n---\n\n".join(history_parts)
                + "\n\n=== End of depot history ==="
            )
        else:
            history_context = ""

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
            history_context=history_context,
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
                system_instruction=RAG_SYSTEM_PROMPT,
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
            sources=doc_sources + case_sources,
        )

    except Exception as exc:
        logger.error("AI analysis failed: %s", exc, exc_info=True)
        return AIResult()
