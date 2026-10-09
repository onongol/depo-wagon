from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from aiogram.utils.formatting import as_list, sizeof

from apps.bot.constants import LIST_NUMBER_EMOJI, TASKS_PAGE_SIZE
from apps.bot.handlers.defect.text import build_fields, build_result_text
from apps.bot.handlers.tasks.text import (
    CARD_MAX_DESCRIPTION,
    CARD_MAX_MEASUREMENTS,
    build_card_text,
    build_status_confirm_text,
    build_status_pick_text,
    build_text_list,
)
from apps.bot.services.defect_card import DefectCard
from apps.bot.user_data import AIResult, DefectData, MeasurementEntry, PhotoEntry
from apps.defects.constants import (
    DefectSeverity,
    DefectStatus,
    DefectType,
    DefectVerdict,
    MeasurementDimension,
)

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
    d.severity = DefectSeverity.HIGH
    d.defect_type = DefectType.CRACK
    d.get_node_display.return_value = "Wheelset"
    d.get_defect_type_display.return_value = "Crack"
    d.get_department_display.return_value = "Repair-1"
    d.part_number = "PN-7"
    d.inspector = MagicMock(full_name="Bat Erdene")
    d.responsible_employee = MagicMock(full_name="Dorj Bold")
    d.inspected_at = datetime(2026, 3, 4, tzinfo=UTC)
    d.description = ""
    d.ai_defect_class = ""
    d.ai_confidence = None
    d.ai_recommendation = ""
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


def _measurement(value="3.50", unit="mm", label="Depth"):
    m = MagicMock()
    m.get_dimension_display.return_value = label
    m.value = Decimal(value)
    m.unit = unit
    m.norm_value = Decimal("2.00")
    return m


def _blocks(card) -> list[str]:
    return _plain(build_card_text(card)).split("\n\n")


class TestBuildCardText:
    def test_the_card_reads_top_down(self):
        blocks = _blocks(_card(verdict=DefectVerdict.REPAIR_NOW))

        assert blocks[0] == "📋 Defect card"
        assert blocks[1].splitlines() == [
            "📊 Status: 🔵 Open",
            "👤 Inspector: Bat Erdene",
            "🕐 Date: 2026-03-04 08:00",
        ]
        assert blocks[2].splitlines() == [
            "🚃 Wagon: 60123456",
            "🏭 Department: Repair-1",
            "🔧 Node: Wheelset",
            "🔢 Part number: PN-7",
            "⚠️ Defect type: Crack",
            "📸 Photos: 3",
            "🌡️ Severity: 🟠 High",
            "👨‍🔧 Verdict: 🟠 Repair Now",
        ]
        assert blocks[3] == "ℹ️ AI analysis is not available."
        assert len(blocks) == 4

    def test_the_fields_read_exactly_as_the_form_shows_them(self):
        card = _card(
            measurements=[_measurement("3.50", "mm", "Depth")],
            defect_type=DefectType.HUMAN_FACTOR,
            description="Worn flange",
            verdict=DefectVerdict.REPAIR_NOW,
        )
        card.defect.get_defect_type_display.return_value = "Human Factor"
        form = DefectData(
            wagon_number="60123456",
            department_label="Repair-1",
            node_label="Wheelset",
            part_number="PN-7",
            defect_type_label="Human Factor",
            responsible_employee_label="Dorj Bold",
            measurements=[
                MeasurementEntry(dimension_label="Depth", value=3.5, unit="mm")
            ],
            photos=[PhotoEntry(file_id=str(i), message_id=i) for i in range(3)],
            description="Worn flange",
            severity_label="🟠 High",
            verdict_label="🟠 Repair Now",
        )

        fields = as_list(*build_fields(form, ())).as_html()

        assert f"\n\n{fields}\n\n" in build_card_text(card).as_html()

    def test_a_closed_defect_says_so(self):
        assert "📊 Status: 🟢 Closed" in _blocks(_card(status=DefectStatus.CLOSED))[1]

    def test_a_missing_inspector_or_date_is_a_dash(self):
        header = _blocks(_card(inspector=None, inspected_at=None))[1]

        assert header.splitlines()[1:] == ["👤 Inspector: —", "🕐 Date: —"]

    def test_what_was_left_empty_is_left_out(self):
        card = _card(part_number="", photo_count=0)

        text = _plain(build_card_text(card))

        for label in (
            "Part number",
            "Measurements",
            "Photos",
            "Description",
            "Verdict",
        ):
            assert label not in text

    def test_a_missing_part_number_is_not_an_empty_entity(self):
        _, entities = build_card_text(_card(part_number="")).render()

        assert all(e.length > 0 for e in entities)

    def test_values_are_bold_as_in_the_form(self):
        html = build_card_text(_card()).as_html()

        assert "🚃 Wagon: <b>60123456</b>" in html
        assert "📊 Status: <b>🔵 Open</b>" in html

    def test_a_human_factor_names_the_responsible(self):
        card = _card(defect_type=DefectType.HUMAN_FACTOR)

        assert "👤 Responsible: Dorj Bold" in _blocks(card)[2].splitlines()

    def test_another_type_has_no_responsible_even_with_one_set(self):
        """The form asks for one only for a human factor."""
        assert "Responsible" not in _plain(build_card_text(_card()))

    def test_a_human_factor_without_a_responsible_has_no_line(self):
        card = _card(defect_type=DefectType.HUMAN_FACTOR, responsible_employee=None)

        assert "Responsible" not in _plain(build_card_text(card))

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

    def test_a_measurement_reads_as_typed_without_its_norm(self):
        card = _card(measurements=[_measurement("3.50", "mm")])

        html = build_card_text(card).as_html()

        assert "🔹 Depth: <b>3.5</b> mm" in html
        assert "norm" not in html

    def test_measurements_past_the_cap_are_only_counted(self):
        card = _card(
            measurements=[_measurement() for _ in range(CARD_MAX_MEASUREMENTS + 3)]
        )

        lines = _plain(build_card_text(card)).splitlines()

        assert f"📐 Measurements: {CARD_MAX_MEASUREMENTS + 3}" in lines
        assert sum(line.startswith("🔹") for line in lines) == CARD_MAX_MEASUREMENTS
        assert "…and 3 more" in lines

    def test_the_description_is_quoted(self):
        html = build_card_text(_card(description="Worn flange")).as_html()

        assert "<blockquote expandable>Worn flange</blockquote>" in html

    def test_a_long_description_is_cut(self):
        text = _plain(build_card_text(_card(description="x" * 1000)))

        assert "x" * (CARD_MAX_DESCRIPTION - 1) + "…" in text
        assert "x" * CARD_MAX_DESCRIPTION not in text

    def test_the_ai_analysis_reads_as_after_the_save(self):
        card = _card(
            ai_defect_class="Thermal crack",
            ai_confidence=Decimal("0.873"),
            ai_verdict=DefectVerdict.REPAIR_NOW,
        )
        result = build_result_text(
            [],
            AIResult(
                defect_class="Thermal crack",
                confidence=0.873,
                verdict=DefectVerdict.REPAIR_NOW,
            ),
        )

        ai = _blocks(card)[-1]

        assert ai == _plain(result).split("\n\n")[-1]
        assert ai.splitlines() == [
            "🤖 AI Analysis:",
            "Defect class:",
            "Thermal crack",
            "Confidence: 87%",
            "AI verdict: 🟠 Repair Now",
        ]

    def test_no_recommendation_and_no_sources(self):
        card = _card(
            ai_defect_class="Thermal crack",
            ai_recommendation="Replace the wheelset",
        )

        text = _plain(build_card_text(card))

        assert "Replace the wheelset" not in text
        assert "Recommendation" not in text
        assert "Sources" not in text

    def test_the_worst_case_still_fits_in_one_message(self):
        longest_label = max(MeasurementDimension.labels, key=len)
        card = _card(
            measurements=[
                _measurement("99999999.99", "U" * 20, longest_label) for _ in range(50)
            ],
            part_number="P" * 100,
            defect_type=DefectType.HUMAN_FACTOR,
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
