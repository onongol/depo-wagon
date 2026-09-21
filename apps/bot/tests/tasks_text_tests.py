from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from aiogram.utils.formatting import sizeof

from apps.bot.constants import LIST_NUMBER_EMOJI, TASKS_PAGE_SIZE
from apps.bot.handlers.tasks.text import (
    CARD_MAX_DESCRIPTION,
    CARD_MAX_MEASUREMENTS,
    build_card_text,
    build_status_confirm_text,
    build_status_pick_text,
    build_text_list,
)
from apps.bot.services.defect_card import DefectCard
from apps.defects.constants import DefectStatus, DefectVerdict, MeasurementDimension

TELEGRAM_TEXT_LIMIT = 4096


def _plain(content) -> str:
    return content.render()[0]


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
        text = _plain(build_text_list([_make_defect()], page=0, total=1, pages=1))

        assert "12345678" in text
        assert "Wheelset" in text
        assert "Crack" in text
        assert "I.Ivanov" in text
        assert "2026-03-04" in text

    def test_a_defect_without_an_inspector_shows_a_dash(self):
        text = _plain(
            build_text_list([_make_defect(inspector=None)], page=0, total=1, pages=1)
        )

        assert "👤 - |" in text

    def test_a_defect_without_an_inspection_date_shows_a_dash(self):
        text = _plain(
            build_text_list([_make_defect(inspected_at=None)], page=0, total=1, pages=1)
        )

        assert text.rstrip().endswith("🕐 -")

    def test_the_wagon_and_node_are_bold(self):
        html = build_text_list([_make_defect()], page=0, total=1, pages=1).as_html()

        assert "<b>12345678 - Wheelset</b>" in html

    def test_markup_in_a_wagon_number_stays_text(self):
        content = build_text_list(
            [_make_defect(number="<b>x</b>")], page=0, total=1, pages=1
        )

        assert "<b>x</b>" in _plain(content)
        assert "&lt;b&gt;x&lt;/b&gt;" in content.as_html()

    def test_header_counts_the_pages(self):
        defects = [_make_defect() for _ in range(TASKS_PAGE_SIZE)]

        text = _plain(
            build_text_list(defects, page=1, total=TASKS_PAGE_SIZE * 2 + 1, pages=3)
        )

        total = TASKS_PAGE_SIZE * 2 + 1
        assert text.splitlines()[0] == f"📋 Open Defects ({total} total, page 2/3)"

    def test_an_empty_list_is_still_page_one_of_one(self):
        text = _plain(build_text_list([], page=0, total=0, pages=1))

        assert text == "📋 Open Defects (0 total, page 1/1)"

    def test_the_entries_are_numbered_like_the_buttons(self):
        defects = [_make_defect(number=str(n)) for n in range(3)]

        text = _plain(build_text_list(defects, page=4, total=100, pages=20))

        entries = text.split("\n\n")[1:]
        assert [e.split()[0] for e in entries] == list(LIST_NUMBER_EMOJI[:3])


def _card_defect(**fields):
    d = MagicMock()
    d.wagon.number = "60123456"
    d.status = DefectStatus.OPEN
    d.severity = "high"
    d.get_node_display.return_value = "Wheelset"
    d.get_defect_type_display.return_value = "Crack"
    d.get_severity_display.return_value = "High"
    d.get_department_display.return_value = "Repair-1"
    d.part_number = "PN-7"
    d.inspector = MagicMock(full_name="Bat Erdene")
    d.responsible_employee = MagicMock(full_name="Dorj Bold")
    d.inspected_at = datetime(2026, 3, 4, tzinfo=UTC)
    d.description = ""
    d.ai_defect_class = ""
    d.ai_confidence = None
    d.ai_verdict = ""
    d.verdict = ""
    for name, value in fields.items():
        setattr(d, name, value)
    return d


def _card(measurements=(), photo_count=3, **fields) -> DefectCard:
    return DefectCard(
        defect=_card_defect(**fields),
        measurements=tuple(measurements),
        photo_count=photo_count,
        targets=(),
    )


def _measurement(value="3.50", unit="mm", norm=None, label="Depth"):
    m = MagicMock()
    m.get_dimension_display.return_value = label
    m.value = Decimal(value)
    m.unit = unit
    m.norm_value = Decimal(norm) if norm else None
    return m


class TestBuildCardText:
    def test_the_core_fields_are_rendered(self):
        text = _plain(build_card_text(_card()))

        for line in (
            "⚠️ Defect: Crack",
            "📊 Status: 🔵 Open",
            "🌡️ Severity: 🟠 High",
            "🚃 Wagon: 60123456",
            "🏭 Department: Repair-1",
            "⚙️ Node: Wheelset",
            "🔢 Part number: PN-7",
            "👤 Inspector: Bat Erdene",
            "🧑‍🔧 Responsible: Dorj Bold",
            "📸 Photos: 3",
        ):
            assert line in text.splitlines()

    def test_labels_are_bold_and_numbers_copyable(self):
        html = build_card_text(_card()).as_html()

        assert "<b>Wagon:</b> <code>60123456</code>" in html
        assert "<b>Part number:</b> <code>PN-7</code>" in html

    def test_the_inspection_time_is_local(self):
        text = _plain(build_card_text(_card()))

        assert "🕐 Date: 2026-03-04 08:00" in text.splitlines()

    def test_a_closed_defect_says_so(self):
        text = _plain(build_card_text(_card(status=DefectStatus.CLOSED)))

        assert "📊 Status: 🟢 Closed" in text

    def test_what_is_missing_shows_a_dash(self):
        card = _card(inspector=None, part_number="", inspected_at=None)
        card.defect.get_department_display.return_value = ""

        text = _plain(build_card_text(card))

        assert text.count(": -") == 4

    def test_the_responsible_employee_is_a_block_of_its_own(self):
        text = _plain(build_card_text(_card()))

        assert "🧑‍🔧 Responsible: Dorj Bold" in text.split("\n\n")

    def test_no_responsible_employee_means_no_line_at_all(self):
        text = _plain(build_card_text(_card(responsible_employee=None)))

        assert "Responsible" not in text

    def test_no_photos_reads_as_zero_not_as_missing(self):
        text = _plain(build_card_text(_card(photo_count=0)))

        assert "📸 Photos: 0" in text.splitlines()

    def test_a_missing_part_number_is_not_an_empty_code_entity(self):
        content = build_card_text(_card(part_number=""))

        _, entities = content.render()
        assert all(e.length > 0 for e in entities)

    def test_everything_people_typed_stays_text(self):
        card = _card(
            part_number="<i>",
            description="<script>",
            ai_defect_class="<u>",
            inspector=MagicMock(full_name="A & B"),
        )
        card.defect.wagon.number = "<b>"

        content = build_card_text(card)

        text, html = _plain(content), content.as_html()
        for raw in ("<i>", "<script>", "<u>", "A & B", "<b>"):
            assert raw in text
        for escaped in ("&lt;i&gt;", "&lt;script&gt;", "&lt;u&gt;", "A &amp; B"):
            assert escaped in html

    def test_a_measurement_shows_its_unit_and_norm(self):
        html = build_card_text(
            _card(measurements=[_measurement(norm="2.00")])
        ).as_html()

        assert "🔹 Depth: <b>3.50</b> mm <i>(norm: 2.00)</i>" in html

    def test_measurements_past_the_cap_are_only_counted(self):
        card = _card(
            measurements=[_measurement() for _ in range(CARD_MAX_MEASUREMENTS + 3)]
        )

        text = _plain(build_card_text(card))

        assert text.count("🔹") == CARD_MAX_MEASUREMENTS
        assert "…and 3 more" in text.splitlines()

    def test_the_description_is_quoted_under_its_label(self):
        html = build_card_text(_card(description="Worn flange")).as_html()

        assert (
            "📝 <b>Description:</b>\n<blockquote expandable>Worn flange</blockquote>"
            in html
        )

    def test_a_long_description_is_cut(self):
        text = _plain(build_card_text(_card(description="x" * 1000)))

        assert "x" * (CARD_MAX_DESCRIPTION - 1) + "…" in text
        assert "x" * CARD_MAX_DESCRIPTION not in text

    def test_no_ai_block_without_an_analysis(self):
        assert "🤖" not in _plain(build_card_text(_card()))

    def test_the_ai_analysis_and_the_verdict(self):
        card = _card(
            ai_defect_class="Thermal crack",
            ai_confidence=Decimal("0.873"),
            ai_verdict=DefectVerdict.REPAIR_NOW,
            verdict=DefectVerdict.OK,
        )

        lines = _plain(build_card_text(card)).splitlines()

        assert lines[-5:] == [
            "🤖 AI:",
            "Thermal crack (87%)",
            "⚖️ AI verdict: 🟠 Repair Now",
            "",
            "✍️ Verdict: ✅ OK",
        ]

    def test_the_ai_class_is_quoted_under_its_label(self):
        card = _card(ai_defect_class="Thermal crack", ai_confidence=Decimal("0.5"))

        html = build_card_text(card).as_html()

        assert (
            "🤖 <b>AI:</b>\n<blockquote expandable>Thermal crack (50%)</blockquote>"
            in html
        )

    def test_an_ai_verdict_without_a_class_still_shows(self):
        text = _plain(build_card_text(_card(ai_verdict=DefectVerdict.OK)))

        assert "🤖" not in text
        assert "⚖️ AI verdict: ✅ OK" in text.splitlines()

    def test_the_worst_case_still_fits_in_one_message(self):
        longest_label = max(MeasurementDimension.labels, key=len)
        card = _card(
            measurements=[
                _measurement("99999999.99", "U" * 20, "99999999.99", longest_label)
                for _ in range(50)
            ],
            part_number="P" * 100,
            inspector=MagicMock(full_name="I" * 201),
            responsible_employee=MagicMock(full_name="R" * 201),
            description="D" * 10_000,
            ai_defect_class="A" * 200,
            ai_confidence=Decimal("1.000"),
            ai_verdict=DefectVerdict.DECOMMISSION,
            verdict=DefectVerdict.DECOMMISSION,
        )
        card.defect.wagon.number = "W" * 20

        text = _plain(build_status_pick_text(card))

        assert sizeof(text) <= TELEGRAM_TEXT_LIMIT


class TestStatusTexts:
    def test_the_confirmation_names_the_defect_and_both_statuses(self):
        text = _plain(build_status_confirm_text(_card_defect(), DefectStatus.CLOSED))

        assert text.split("\n\n") == [
            "Change the status?",
            "🚃 60123456 - Wheelset",
            "🔵 Open → 🟢 Closed",
        ]

    def test_markup_in_the_confirmation_stays_text(self):
        defect = _card_defect()
        defect.wagon.number = "<b>1</b>"

        html = build_status_confirm_text(defect, DefectStatus.CLOSED).as_html()

        assert "&lt;b&gt;1&lt;/b&gt;" in html

    def test_the_picker_keeps_the_card_above_the_question(self):
        card = _card()

        text = _plain(build_status_pick_text(card))

        assert text.startswith(_plain(build_card_text(card)))
        assert text.endswith("⚙️ Choose the new status:")
