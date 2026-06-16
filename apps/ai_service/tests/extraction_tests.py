import io
from unittest.mock import MagicMock, patch

from apps.ai_service.processing.extraction import extract_pages


def _make_page(text):
    page = MagicMock()
    page.extract_text.return_value = text
    return page


def _extract(pages_text):
    mock_pages = [_make_page(t) for t in pages_text]
    with patch("apps.ai_service.processing.extraction.PdfReader") as MockPdf:
        MockPdf.return_value.pages = mock_pages
        return extract_pages(io.BytesIO(b"fake pdf"))


class TestExtractPages:
    def test_single_page_returns_page_number_and_text(self):
        result = _extract(["Page one text"])
        assert result == [(1, "Page one text")]

    def test_multiple_pages_numbered_from_one(self):
        result = _extract(["First", "Second", "Third"])
        assert result == [(1, "First"), (2, "Second"), (3, "Third")]

    def test_empty_pages_filtered_out(self):
        result = _extract(["", "Real content", ""])
        assert result == [(2, "Real content")]

    def test_whitespace_only_pages_filtered_out(self):
        result = _extract(["   \n  ", "Good text"])
        assert result == [(2, "Good text")]

    def test_none_text_filtered_out(self):
        result = _extract([None, "Valid text"])
        assert result == [(2, "Valid text")]

    def test_all_empty_returns_empty_list(self):
        result = _extract(["", "   ", None])
        assert result == []

    def test_page_numbering_skips_empty_pages_correctly(self):
        result = _extract(["", "Second page text", "", "Fourth page text"])
        assert result == [(2, "Second page text"), (4, "Fourth page text")]
