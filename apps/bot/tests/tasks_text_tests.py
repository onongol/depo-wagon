from datetime import UTC, datetime
from unittest.mock import MagicMock

from apps.bot.constants import PAGE_SIZE
from apps.bot.handlers.tasks.text import build_text


def _make_defect(
    number="12345678",
    inspector="I.Ivanov",
    inspected_at=datetime(2026, 3, 4, tzinfo=UTC),
):
    d = MagicMock()
    d.severity = "high"
    d.status = "open"
    d.wagon.number = number
    d.get_node_display.return_value = "Wheelset"
    d.get_defect_type_display.return_value = "Crack"
    d.inspector = MagicMock(short_name=inspector) if inspector else None
    d.inspected_at = inspected_at
    return d


class TestBuildText:
    def test_defect_fields_are_rendered(self):
        text = build_text([_make_defect()], page=0, total=1)

        assert "12345678" in text
        assert "Wheelset" in text
        assert "Crack" in text
        assert "I.Ivanov" in text
        assert "2026-03-04" in text

    def test_a_defect_without_an_inspector_shows_a_dash(self):
        text = build_text([_make_defect(inspector=None)], page=0, total=1)

        assert "👤 — |" in text

    def test_a_defect_without_an_inspection_date_shows_a_dash(self):
        text = build_text([_make_defect(inspected_at=None)], page=0, total=1)

        assert text.rstrip().endswith("🕐 —")

    def test_html_in_a_wagon_number_is_escaped(self):
        text = build_text([_make_defect(number="<b>x</b>")], page=0, total=1)

        assert "&lt;b&gt;x&lt;/b&gt;" in text

    def test_header_counts_the_current_page(self):
        defects = [_make_defect() for _ in range(PAGE_SIZE)]

        text = build_text(defects, page=1, total=12)

        assert "12" in text.splitlines()[0]

    def test_the_last_page_stops_at_the_total(self):
        text = build_text([_make_defect()], page=2, total=11)

        header = text.splitlines()[0]
        assert "11" in header
