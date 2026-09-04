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


async def _describe_photos(photos_bytes: list[bytes] | None) -> str:
    """Visual description for query augmentation; empty when unavailable."""
    if not photos_bytes:
        return ""
    try:
        return await describe_images(photos_bytes)
    except Exception as exc:
        logger.warning("Image description failed: %s", exc, exc_info=True)
        return ""


def _build_query_text(
    node: str, defect_type: str, severity: str, description: str, visual_desc: str
) -> str:
    parts = [
        f"Node/Element: {node}",
        f"Defect type: {defect_type}",
        f"Severity: {severity}",
    ]
    if description:
        parts.append(f"Description: {description}")
    if visual_desc:
        parts.append(f"Visual signs: {visual_desc}")
    return "\n".join(parts)


def _build_doc_context(chunks: list[dict]) -> tuple[str, list[str]]:
    """Reference-material block for the prompt, and the source labels shown to the user."""
    if not chunks:
        return "(No depot documents found — use general technical knowledge.)", []

    context_parts = []
    pages_by_title: dict[str, list[int]] = {}
    for i, chunk in enumerate(chunks, 1):
        title = chunk["document__title"]
        page = chunk.get("page_number")
        pages_by_title.setdefault(title, [])
        if page:
            pages_by_title[title].append(page)
        source = f"{title}, p. {page}" if page else title
        context_parts.append(f"[DOC-{i}] {source}:\n{chunk['content']}")

    sources = [
        f"📄 {title}, p. {', '.join(str(p) for p in sorted(set(pages)))}"
        if pages
        else f"📄 {title}"
        for title, pages in pages_by_title.items()
    ]
    context = (
        "=== Reference materials from depot documents ===\n\n"
        + "\n\n---\n\n".join(context_parts)
        + "\n\n=== End of reference materials ==="
    )
    return context, sources


def _build_history_context(past_defects: list[dict]) -> tuple[str, list[str]]:
    """Precedent-cases block for the prompt, and its source label."""
    if not past_defects:
        return "", []

    history_parts = [
        f"[CASE-{i}] {defect['created_at'].strftime('%m.%Y')}:\n{defect['content']}"
        for i, defect in enumerate(past_defects, 1)
    ]
    context = (
        "=== Similar cases from depot history ===\n\n"
        + "\n\n---\n\n".join(history_parts)
        + "\n\n=== End of depot history ==="
    )
    return context, [f"🔁 {len(past_defects)} precedent cases"]


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

    Degrades to an empty AIResult rather than raising on an AI or retrieval
    failure. Bugs in the context builders propagate to the caller, which logs
    them with a traceback.
    """
    client = get_genai_client()

    visual_desc = await _describe_photos(photos_bytes)
    query_text = _build_query_text(
        node, defect_type, severity, description, visual_desc
    )

    try:
        query_embedding = await embed_query(query_text)
    except Exception as exc:
        logger.warning("Embedding failed, skipping AI analysis: %s", exc, exc_info=True)
        return AIResult()

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

    rag_context, doc_sources = _build_doc_context(chunks)
    history_context, case_sources = _build_history_context(past_defects)

    description_line = (
        f"<user_description>\n{description}\n</user_description>" if description else ""
    )
    prompt = ANALYSIS_PROMPT.format(
        node=node,
        defect_type=defect_type,
        severity=severity,
        description_line=description_line,
        rag_context=rag_context,
        history_context=history_context,
    )

    contents: list = [
        types.Part.from_bytes(data=photo, mime_type=mime_type_for_bytes(photo))
        for photo in photos_bytes or []
    ]
    contents.append(prompt)

    try:
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
    except Exception:
        logger.exception("AI analysis failed")
        return AIResult()

    return AIResult(
        defect_class=result.defect_class,
        confidence=result.confidence,
        rag_recommendation=result.rag_recommendation,
        verdict=result.verdict,
        sources=doc_sources + case_sources,
    )
