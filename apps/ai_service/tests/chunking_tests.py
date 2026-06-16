from apps.ai_service.processing.chunking import chunk_page


class TestChunkPage:
    def test_empty_text_returns_empty(self):
        assert chunk_page("", 1) == []

    def test_whitespace_only_returns_empty(self):
        assert chunk_page("   \n\t  ", 3) == []

    def test_short_text_produces_single_chunk(self):
        result = chunk_page("Hello world", 1)
        assert len(result) == 1
        assert result[0]["content"] == "Hello world"
        assert result[0]["page_number"] == 1

    def test_page_number_propagated_to_all_chunks(self):
        result = chunk_page("Some text here", 7)
        assert all(c["page_number"] == 7 for c in result)

    def test_long_text_splits_into_multiple_chunks(self):
        # Chunk size is 2000 chars; 5000-char text must split
        long_text = "word " * 1000
        result = chunk_page(long_text, 2)
        assert len(result) > 1

    def test_all_chunks_have_non_empty_content(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = chunk_page(text, 1)
        assert result
        assert all(c["content"].strip() for c in result)

    def test_each_chunk_has_required_keys(self):
        result = chunk_page("Some content", 4)
        for chunk in result:
            assert "content" in chunk
            assert "page_number" in chunk
