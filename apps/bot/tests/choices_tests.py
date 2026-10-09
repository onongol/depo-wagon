import pytest

from apps.bot.constants import SEVERITY_EMOJI, STATUS_EMOJI, VERDICT_EMOJI
from apps.bot.utils.choices import choice_label, emoji_choices, emoji_label
from apps.defects.constants import DefectSeverity, DefectStatus, DefectVerdict


@pytest.mark.parametrize(
    ("emoji", "choices"),
    [
        (SEVERITY_EMOJI, DefectSeverity),
        (VERDICT_EMOJI, DefectVerdict),
        (STATUS_EMOJI, DefectStatus),
    ],
)
def test_every_choice_has_an_emoji(emoji, choices):
    assert set(emoji) == set(choices)


class TestChoiceLabel:
    def test_a_known_value_gives_its_label(self):
        assert choice_label(DefectVerdict, "repair_soon") == "Repair Soon"

    def test_an_unknown_value_gives_itself(self):
        assert choice_label(DefectVerdict, "bogus") == "bogus"

    def test_an_unknown_value_gives_the_default(self):
        assert choice_label(DefectVerdict, "bogus", "-") == "-"


class TestEmojiLabel:
    def test_a_known_value_gets_its_emoji(self):
        assert emoji_label(SEVERITY_EMOJI, DefectSeverity, "high") == "🟠 High"

    def test_an_unknown_value_shows_as_is(self):
        assert emoji_label(SEVERITY_EMOJI, DefectSeverity, "bogus") == "bogus"

    def test_an_empty_value_stays_empty(self):
        assert emoji_label(VERDICT_EMOJI, DefectVerdict, "") == ""


def test_emoji_choices_keep_the_enum_order():
    assert emoji_choices(STATUS_EMOJI, DefectStatus) == [
        ("🔵 Open", "open"),
        ("🟡 In Progress", "in_progress"),
        ("🟢 Closed", "closed"),
    ]
