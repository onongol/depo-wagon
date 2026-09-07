from unittest.mock import MagicMock, patch

import pytest

from apps.ai_service.processing.embedding import BATCH_SIZE, embed_texts


def _mock_client(responses_per_call):
    """Mock genai client whose embed_content returns the responses in order."""
    mock_responses = []
    for emb_vectors in responses_per_call:
        resp = MagicMock()
        resp.embeddings = [MagicMock(values=v) for v in emb_vectors]
        mock_responses.append(resp)
    client = MagicMock()
    client.models.embed_content.side_effect = mock_responses
    return client


class TestEmbedTexts:
    def test_empty_input_returns_empty_list(self):
        client = MagicMock()
        with patch(
            "apps.ai_service.processing.embedding.get_genai_client", return_value=client
        ):
            result = embed_texts([])
        assert result == []
        client.models.embed_content.assert_not_called()

    def test_single_text_returns_single_embedding(self):
        vector = [0.1, 0.2, 0.3]
        client = _mock_client([[vector]])
        with patch(
            "apps.ai_service.processing.embedding.get_genai_client", return_value=client
        ):
            result = embed_texts(["hello world"])
        assert result == [vector]

    def test_multiple_texts_within_one_batch(self):
        vectors = [[float(i)] for i in range(3)]
        client = _mock_client([vectors])
        with patch(
            "apps.ai_service.processing.embedding.get_genai_client", return_value=client
        ):
            result = embed_texts(["a", "b", "c"])
        assert result == vectors

    def test_large_input_triggers_two_api_calls(self):
        batch1 = [[0.1]] * BATCH_SIZE
        batch2 = [[0.2]] * 10
        client = _mock_client([batch1, batch2])
        with patch(
            "apps.ai_service.processing.embedding.get_genai_client", return_value=client
        ):
            result = embed_texts(["text"] * (BATCH_SIZE + 10))
        assert len(result) == BATCH_SIZE + 10
        assert client.models.embed_content.call_count == 2

    def test_retries_on_rate_limit_429(self):
        from google.genai.errors import ClientError

        vector = [0.5, 0.6]
        client = MagicMock()
        rate_limit_error = ClientError(
            429, {"message": "Rate limited", "status": "RESOURCE_EXHAUSTED"}
        )
        success_resp = MagicMock()
        success_resp.embeddings = [MagicMock(values=vector)]
        client.models.embed_content.side_effect = [rate_limit_error, success_resp]

        with (
            patch(
                "apps.ai_service.processing.embedding.get_genai_client",
                return_value=client,
            ),
            patch("apps.ai_service.processing.embedding.time.sleep"),
        ):
            result = embed_texts(["hello"])

        assert result == [vector]
        assert client.models.embed_content.call_count == 2

    def test_raises_immediately_on_non_429_error(self):
        from google.genai.errors import ClientError

        client = MagicMock()
        client.models.embed_content.side_effect = ClientError(
            400, {"message": "Bad request"}
        )

        with (
            patch(
                "apps.ai_service.processing.embedding.get_genai_client",
                return_value=client,
            ),
            pytest.raises(ClientError) as exc_info,
        ):
            embed_texts(["hello"])

        assert exc_info.value.code == 400
        assert client.models.embed_content.call_count == 1

    def test_exhausted_retries_raise_429(self):
        from google.genai.errors import ClientError

        client = MagicMock()
        rate_limit_error = ClientError(
            429, {"message": "Rate limited", "status": "RESOURCE_EXHAUSTED"}
        )
        client.models.embed_content.side_effect = [rate_limit_error] * 10

        with (
            patch(
                "apps.ai_service.processing.embedding.get_genai_client",
                return_value=client,
            ),
            patch("apps.ai_service.processing.embedding.time.sleep"),
            pytest.raises(ClientError) as exc_info,
        ):
            embed_texts(["hello"])

        assert exc_info.value.code == 429
