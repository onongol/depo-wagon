import pytest

from apps.bot.utils.formatting import MESSAGE_LIMIT, split_message, utf16_len


class TestSplitMessage:
    def test_a_message_that_fits_stays_whole(self):
        assert split_message("short answer") == ["short answer"]

    def test_exactly_the_limit_stays_whole(self):
        value = "x" * MESSAGE_LIMIT

        assert split_message(value) == [value]

    def test_breaks_after_the_last_line_that_fits(self):
        first, second = "a" * 3000, "b" * 3000

        assert split_message(f"{first}\n\n{second}") == [first, second]

    def test_breaks_between_words_when_no_line_fits(self):
        words = " ".join(["word"] * 1000)

        pieces = split_message(words)

        assert len(pieces) == 2
        assert all(set(piece.split(" ")) == {"word"} for piece in pieces)

    def test_a_line_break_too_early_is_passed_over_for_a_space(self):
        """A heading alone would leave a short first message."""
        value = "Heading\n" + " ".join(["word"] * 1000)

        first, _ = split_message(value)

        assert first.startswith("Heading\nword")

    def test_text_with_no_break_is_cut_hard(self):
        value = "x" * (MESSAGE_LIMIT + 10)

        assert split_message(value) == ["x" * MESSAGE_LIMIT, "x" * 10]

    @pytest.mark.parametrize("char", ["😀", "А", "x"])
    def test_every_piece_fits_in_utf16_units(self, char):
        """An emoji is two units: a plain len() would let the piece run over."""
        value = char * (MESSAGE_LIMIT + 1)

        pieces = split_message(value)

        assert all(utf16_len(piece) <= MESSAGE_LIMIT for piece in pieces)
        assert "".join(pieces) == value
