from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch


class TestAnswerQuestion:
    def _make_client(self, text="AI answer"):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = text
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_response)
        return mock_client

    def _patches(self, client, chunks=None, defects=None):
        return [
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=chunks or []),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=defects or []),
            ),
        ]

    async def test_returns_genai_response_text(self):
        from apps.ai_service.rag.chat import answer_question

        client = self._make_client("Ответ по УЗ контролю")
        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            result = await answer_question("Как провести УЗ контроль?", [])

        assert result == "Ответ по УЗ контролю"

    async def test_empty_response_returns_empty_string(self):
        from apps.ai_service.rag.chat import answer_question

        client = self._make_client(None)
        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            result = await answer_question("вопрос", [])

        assert result == ""

    async def test_includes_document_chunks_in_context(self):
        from apps.ai_service.rag.chat import answer_question

        chunks = [
            {
                "document__title": "Инструкция ТО",
                "page_number": 5,
                "content": "Норма износа 2 мм",
            }
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=chunks),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("норма износа", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        last_content = call_kwargs["contents"][-1]
        user_text = last_content.parts[0].text
        assert "Инструкция ТО" in user_text
        assert "Норма износа 2 мм" in user_text
        assert "стр.5" in user_text

    async def test_includes_defect_history_in_context(self):
        from apps.ai_service.rag.chat import answer_question

        defects = [{"content": "трещина обода колеса", "created_at": date(2024, 3, 15)}]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=defects),
            ),
        ):
            await answer_question("дефекты колёс", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        last_content = call_kwargs["contents"][-1]
        user_text = last_content.parts[0].text
        assert "трещина обода колеса" in user_text
        assert "15.03.2024" in user_text

    async def test_no_context_sends_raw_question(self):
        from apps.ai_service.rag.chat import answer_question

        client = self._make_client()
        question = "Что такое колёсная пара?"

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question(question, [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        last_content = call_kwargs["contents"][-1]
        assert last_content.parts[0].text == question

    async def test_history_messages_prepended_to_contents(self):
        from apps.ai_service.rag.chat import answer_question

        history = [
            {"role": "user", "content": "Первый вопрос"},
            {"role": "model", "content": "Первый ответ"},
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("Второй вопрос", history)

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        contents = call_kwargs["contents"]
        # 2 history messages + 1 current question
        assert len(contents) == 3
        assert contents[0].role == "user"
        assert contents[1].role == "model"
        assert contents[2].role == "user"

    async def test_history_truncated_to_max(self):
        from apps.ai_service.rag.chat import _MAX_HISTORY, answer_question

        history = [
            {"role": "user" if i % 2 == 0 else "model", "content": f"msg {i}"}
            for i in range(_MAX_HISTORY + 4)
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("новый вопрос", history)

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        contents = call_kwargs["contents"]
        # At most _MAX_HISTORY history messages + 1 current question
        assert len(contents) <= _MAX_HISTORY + 1

    async def test_uses_chat_system_prompt(self):
        from apps.ai_service.rag.chat import answer_question
        from apps.ai_service.rag.config import CHAT_SYSTEM_PROMPT

        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("вопрос", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        assert call_kwargs["config"].system_instruction == CHAT_SYSTEM_PROMPT

    async def test_embeds_question_before_retrieval(self):
        from apps.ai_service.rag.chat import answer_question

        embed_mock = AsyncMock(return_value=[0.5] * 1536)
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch("apps.ai_service.rag.chat.embed_query", embed_mock),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("вопрос про ось", [])

        embed_mock.assert_awaited_once_with("вопрос про ось")

    async def test_malformed_history_entries_are_skipped(self):
        from apps.ai_service.rag.chat import answer_question

        history = [
            {"role": "user", "content": "нормальный вопрос"},
            {"role": "model"},  # нет content
            {"content": "нет роли"},  # нет role
            {"role": "admin", "content": "чужая роль"},  # role не "user"/"model"
            {"role": "model", "content": "нормальный ответ"},
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("новый вопрос", history)

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        contents = call_kwargs["contents"]
        # только 2 валидных + 1 текущий вопрос
        assert len(contents) == 3
        assert contents[0].role == "user"
        assert contents[1].role == "model"

    async def test_defect_without_created_at_uses_content_only(self):
        from apps.ai_service.rag.chat import answer_question

        defects = [{"content": "износ реборды", "created_at": None}]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=defects),
            ),
        ):
            result = await answer_question("реборда", [])

        assert result == "AI answer"

    # --- Fix 1: timeout ---

    async def test_embed_timeout_raises(self):
        import asyncio
        from apps.ai_service.rag.chat import answer_question

        async def slow_embed(_):
            await asyncio.sleep(100)

        with (
            patch("apps.ai_service.rag.chat.embed_query", slow_embed),
            patch("apps.ai_service.rag.chat._EMBED_TIMEOUT", 0.01),
        ):
            import pytest

            with pytest.raises(asyncio.TimeoutError):
                await answer_question("вопрос", [])

    # --- Fix 2: retrieval failure degrades gracefully ---

    async def test_chunks_failure_still_returns_answer(self):
        from apps.ai_service.rag.chat import answer_question

        client = self._make_client("ответ без документов")

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(side_effect=RuntimeError("db down")),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            result = await answer_question("вопрос", [])

        assert result == "ответ без документов"

    async def test_defects_failure_still_returns_answer(self):
        from apps.ai_service.rag.chat import answer_question

        client = self._make_client("ответ без дефектов")

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(side_effect=RuntimeError("db down")),
            ),
        ):
            result = await answer_question("вопрос", [])

        assert result == "ответ без дефектов"

    # --- Fix 3: context size cap ---

    async def test_context_truncated_when_too_long(self):
        from apps.ai_service.rag.chat import _MAX_CONTEXT_CHARS, answer_question

        huge_chunk = [
            {
                "document__title": "Doc",
                "page_number": 1,
                "content": "x" * (_MAX_CONTEXT_CHARS + 500),
            }
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=huge_chunk),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("вопрос", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        user_text = call_kwargs["contents"][-1].parts[0].text
        assert "[контекст обрезан]" in user_text
        assert len(user_text) < _MAX_CONTEXT_CHARS + 200

    # --- Fix 4 & 5: missing fields in chunks/defects ---

    async def test_chunk_without_content_is_skipped(self):
        from apps.ai_service.rag.chat import answer_question

        chunks = [
            {"document__title": "Doc", "page_number": 1, "content": ""},
            {
                "document__title": "Doc2",
                "page_number": 2,
                "content": "реальный контент",
            },
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=chunks),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("вопрос", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        user_text = call_kwargs["contents"][-1].parts[0].text
        assert "реальный контент" in user_text
        assert "Doc2" in user_text

    async def test_chunk_missing_title_uses_placeholder(self):
        from apps.ai_service.rag.chat import answer_question

        chunks = [{"content": "текст без заголовка"}]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=chunks),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            await answer_question("вопрос", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        user_text = call_kwargs["contents"][-1].parts[0].text
        assert "[?," in user_text

    async def test_defect_without_content_is_skipped(self):
        from apps.ai_service.rag.chat import answer_question

        defects = [
            {"content": None, "created_at": None},
            {"content": "реальный дефект", "created_at": None},
        ]
        client = self._make_client()

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=defects),
            ),
        ):
            await answer_question("вопрос", [])

        call_kwargs = client.aio.models.generate_content.call_args.kwargs
        user_text = call_kwargs["contents"][-1].parts[0].text
        assert "реальный дефект" in user_text

    # --- Fix 6: safety filter ---

    async def test_safety_block_raises_content_blocked_error(self):
        from google.genai import types
        from apps.ai_service.rag.chat import ContentBlockedError, answer_question
        import pytest

        candidate = MagicMock()
        candidate.finish_reason = types.FinishReason.SAFETY
        mock_response = MagicMock()
        mock_response.candidates = [candidate]
        mock_response.text = None
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            with pytest.raises(ContentBlockedError):
                await answer_question("вопрос", [])

    async def test_no_candidates_raises_content_blocked_error(self):
        from apps.ai_service.rag.chat import ContentBlockedError, answer_question
        import pytest

        mock_response = MagicMock()
        mock_response.candidates = []
        mock_response.text = None
        client = MagicMock()
        client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with (
            patch("apps.ai_service.rag.chat.get_genai_client", return_value=client),
            patch(
                "apps.ai_service.rag.chat.embed_query",
                AsyncMock(return_value=[0.1] * 1536),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_chunks",
                AsyncMock(return_value=[]),
            ),
            patch(
                "apps.ai_service.rag.chat.fetch_similar_defects",
                AsyncMock(return_value=[]),
            ),
        ):
            with pytest.raises(ContentBlockedError):
                await answer_question("вопрос", [])
