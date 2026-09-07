import asyncio

from google.genai import types

from apps.ai_service.client import get_genai_client
from apps.ai_service.config import GENERATION_MODEL
from apps.ai_service.rag.config import CHAT_SYSTEM_PROMPT
from apps.ai_service.rag.embedding import embed_query
from apps.ai_service.rag.retrieval.chunks import fetch_similar_chunks
from apps.ai_service.rag.retrieval.defects import fetch_similar_defects

_MAX_HISTORY = 6  # messages kept in context (3 Q&A pairs)
_EMBED_TIMEOUT = 15.0  # seconds before embed_query is considered hung
_MAX_CONTEXT_CHARS = 8000  # ~2k tokens; keeps prompt cost predictable

_SAFETY_FINISH_REASONS = {
    types.FinishReason.SAFETY,
    types.FinishReason.PROHIBITED_CONTENT,
    types.FinishReason.BLOCKLIST,
    types.FinishReason.SPII,
}


class ContentBlockedError(Exception):
    """Raised when Gemini's safety filters block the response."""


def _or_empty(result) -> list[dict]:
    """A gathered retrieval result, or an empty list when that branch failed."""
    return [] if isinstance(result, BaseException) else result


def _format_chunk(chunk: dict) -> str:
    """One chunk as a labelled context entry."""
    # .get() with defaults so a schema change doesn't raise KeyError
    title = chunk.get("document__title", "?")
    page = chunk.get("page_number", "?")
    content = chunk.get("content", "")
    return f"[{title}, p.{page}]\n{content}"


def _docs_block(chunks: list[dict]) -> str:
    """Depot-documents context section, empty when nothing usable came back."""
    docs_text = "\n\n".join(
        _format_chunk(chunk) for chunk in chunks if chunk.get("content")
    )
    return f"=== Depot Documents ===\n{docs_text}" if docs_text else ""


def _defects_block(defects: list[dict]) -> str:
    """Defect-history context section, empty when nothing usable came back."""
    lines: list[str] = []
    for defect in defects:
        content = defect.get("content")
        if not content:
            continue
        created_at = defect.get("created_at")
        prefix = (
            f"[Defect from {created_at.strftime('%d.%m.%Y')}]\n" if created_at else ""
        )
        lines.append(f"{prefix}{content}")
    return ("=== Defect History ===\n" + "\n\n".join(lines)) if lines else ""


def _build_contents(history: list[dict], user_text: str) -> list[types.Content]:
    """Chat history as Content parts, malformed entries dropped, question appended."""
    contents = [
        types.Content(
            role=msg["role"], parts=[types.Part.from_text(text=msg["content"])]
        )
        for msg in history[-_MAX_HISTORY:]
        if msg.get("role") in {"user", "model"} and isinstance(msg.get("content"), str)
    ]
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_text)])
    )
    return contents


async def answer_question(question: str, history: list[dict]) -> str:
    """Answer a free-form depot question using RAG over documents and defect history."""

    # Timeout so a hung Embedding API never freezes the handler forever
    embedding = await asyncio.wait_for(embed_query(question), timeout=_EMBED_TIMEOUT)

    # Return_exceptions=True so a retrieval failure degrades gracefully
    # (empty context) instead of cancelling the sibling coroutine mid-flight
    results = await asyncio.gather(
        fetch_similar_chunks(embedding, question),
        fetch_similar_defects(embedding, question),
        return_exceptions=True,
    )
    blocks = (_docs_block(_or_empty(results[0])), _defects_block(_or_empty(results[1])))
    context_parts = [block for block in blocks if block]

    user_text = question
    if context_parts:
        context_block = "\n\n".join(context_parts)
        if len(context_block) > _MAX_CONTEXT_CHARS:
            context_block = context_block[:_MAX_CONTEXT_CHARS] + "\n[context truncated]"
        user_text = f"Context:\n{context_block}\n\nQuestion: {question}"

    response = await get_genai_client().aio.models.generate_content(
        model=GENERATION_MODEL,
        contents=_build_contents(history, user_text),
        config=types.GenerateContentConfig(
            system_instruction=CHAT_SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=1500,
        ),
    )

    # Distinguish safety block from an empty-but-valid response
    if not response.candidates:
        raise ContentBlockedError
    if response.candidates[0].finish_reason in _SAFETY_FINISH_REASONS:
        raise ContentBlockedError

    return response.text or ""
