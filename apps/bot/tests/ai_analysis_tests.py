import pytest
from pydantic import ValidationError

from apps.bot.ai_analysis import _parse_response
from apps.bot.user_data import AIResult
from apps.defects.constants import DefectVerdict


def _make_json(verdict="repair_now", confidence=0.9):
    return (
        f'{{"defect_class": "Трещина обода колеса", "confidence": {confidence},'
        f' "recommendation": "Заменить колёсную пару.", "verdict": "{verdict}"}}'
    )


class TestParseResponse:
    def test_returns_ai_result(self):
        result = _parse_response(_make_json())
        assert isinstance(result, AIResult)

    def test_maps_all_fields(self):
        result = _parse_response(_make_json(verdict="ok", confidence=0.75))
        assert result.defect_class == "Трещина обода колеса"
        assert result.confidence == 0.75
        assert result.recommendation == "Заменить колёсную пару."
        assert result.verdict == DefectVerdict.OK

    @pytest.mark.parametrize("verdict", [v.value for v in DefectVerdict])
    def test_all_valid_verdicts(self, verdict):
        result = _parse_response(_make_json(verdict=verdict))
        assert result.verdict == DefectVerdict(verdict)

    def test_invalid_verdict_raises(self):
        with pytest.raises(ValidationError):
            _parse_response(_make_json(verdict="unknown_status"))

    def test_invalid_json_raises(self):
        with pytest.raises(ValidationError):
            _parse_response("not json at all")
