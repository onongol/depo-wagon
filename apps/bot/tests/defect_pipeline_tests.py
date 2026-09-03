from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import Forbidden

from apps.bot.handlers.defect.confirm.pipeline import (
    PersistResult,
    register_defect,
    run_ai_analysis,
)
from apps.bot.handlers.defect.notifications import notify_decommission
from apps.bot.user_data import DefectData, MeasurementEntry


def _make_defect_data(**kwargs):
    data = DefectData(
        wagon_id=kwargs.get("wagon_id", 1),
        wagon_number=kwargs.get("wagon_number", "12345"),
        node=kwargs.get("node", "wheel"),
        node_label=kwargs.get("node_label", "Wheel"),
        defect_type=kwargs.get("defect_type", "crack"),
        defect_type_label=kwargs.get("defect_type_label", "Crack"),
        severity=kwargs.get("severity", "high"),
        severity_label=kwargs.get("severity_label", "High"),
        description=kwargs.get("description", "Defect description"),
        department=kwargs.get("department", "bogie"),
        part_number=kwargs.get("part_number", ""),
        photo_file_ids=kwargs.get("photo_file_ids", []),
        measurements=kwargs.get("measurements", []),
    )
    return data


def _make_saved_defect(defect_id="uuid-001"):
    defect = MagicMock()
    defect.id = defect_id
    return defect


def _make_bot_file(size=1000, content=b"fake image"):
    mock_file = MagicMock()
    mock_file.file_size = size
    mock_file.download_as_bytearray = AsyncMock(return_value=bytearray(content))
    return mock_file


class TestRegisterDefect:
    async def test_saves_defect_and_returns_result(self):
        saved = _make_saved_defect()
        bot = AsyncMock()
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=saved)
            result = await register_defect(
                _make_defect_data(), employee=MagicMock(), bot=bot
            )
        assert isinstance(result, PersistResult)
        assert result.defect is saved

    async def test_no_photos_returns_empty_photo_bytes(self):
        bot = AsyncMock()
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            result = await register_defect(
                _make_defect_data(photo_file_ids=[]), employee=MagicMock(), bot=bot
            )
        assert result.photo_bytes == []

    async def test_photo_downloaded_and_returned(self):
        bot = AsyncMock()
        bot.get_file = AsyncMock(return_value=_make_bot_file(content=b"img"))
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.create_photo_from_bytes = AsyncMock()
            result = await register_defect(
                _make_defect_data(photo_file_ids=["file123"]),
                employee=MagicMock(),
                bot=bot,
            )
        assert len(result.photo_bytes) == 1
        assert result.photo_bytes[0] == b"img"

    async def test_photo_download_failure_is_non_critical(self):
        bot = AsyncMock()
        bot.get_file = AsyncMock(side_effect=Exception("Telegram timeout"))
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            result = await register_defect(
                _make_defect_data(photo_file_ids=["file123"]),
                employee=MagicMock(),
                bot=bot,
            )
        assert result.photo_bytes == []

    async def test_oversized_photo_is_skipped(self):
        bot = AsyncMock()
        bot.get_file = AsyncMock(return_value=_make_bot_file(size=99_999_999))
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            result = await register_defect(
                _make_defect_data(photo_file_ids=["big_file"]),
                employee=MagicMock(),
                bot=bot,
            )
        assert result.photo_bytes == []

    async def test_one_photo_fail_does_not_block_others(self):
        good_file = _make_bot_file(content=b"ok")
        bad_file = MagicMock()
        bad_file.file_size = 100
        bad_file.download_as_bytearray = AsyncMock(
            side_effect=Exception("network error")
        )

        bot = AsyncMock()
        bot.get_file = AsyncMock(side_effect=[bad_file, good_file])

        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.create_photo_from_bytes = AsyncMock()
            result = await register_defect(
                _make_defect_data(photo_file_ids=["bad", "good"]),
                employee=MagicMock(),
                bot=bot,
            )
        assert len(result.photo_bytes) == 1

    async def test_measurements_saved_when_present(self):
        measurements = [MeasurementEntry(dimension="width", value=5.0)]
        bot = AsyncMock()
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect("id-99"))
            svc.create_measurements_bulk = AsyncMock()
            await register_defect(
                _make_defect_data(measurements=measurements),
                employee=MagicMock(),
                bot=bot,
            )
        svc.create_measurements_bulk.assert_awaited_once_with("id-99", measurements)

    async def test_measurements_failure_is_non_critical(self):
        measurements = [MeasurementEntry(dimension="width", value=5.0)]
        bot = AsyncMock()
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.create_measurements_bulk = AsyncMock(side_effect=Exception("db locked"))
            result = await register_defect(
                _make_defect_data(measurements=measurements),
                employee=MagicMock(),
                bot=bot,
            )
        assert result.defect is not None

    async def test_create_defect_failure_raises(self):
        import pytest

        bot = AsyncMock()
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(side_effect=Exception("db down"))
            with pytest.raises(Exception, match="db down"):
                await register_defect(
                    _make_defect_data(), employee=MagicMock(), bot=bot
                )


class TestRunAiAnalysis:
    async def test_returns_ai_result_on_success(self):
        ai_result = MagicMock()
        ai_result.defect_class = "crack"
        ai_result.confidence = 0.95
        ai_result.rag_recommendation = "replace"
        ai_result.verdict = "critical"

        with (
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.analyze_defect",
                AsyncMock(return_value=ai_result),
            ),
            patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc,
        ):
            svc.update_defect_ai_result = AsyncMock()
            result = await run_ai_analysis(
                _make_defect_data(), defect_id="id-1", photo_bytes=[b"img"]
            )

        assert result is ai_result

    async def test_analyze_exception_returns_none(self):
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.analyze_defect",
            AsyncMock(side_effect=Exception("model timeout")),
        ):
            result = await run_ai_analysis(
                _make_defect_data(), defect_id="id-1", photo_bytes=[]
            )

        assert result is None

    async def test_analyze_exception_never_raises(self):
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.analyze_defect",
            AsyncMock(side_effect=RuntimeError("crash")),
        ):
            await run_ai_analysis(_make_defect_data(), defect_id="id-1", photo_bytes=[])

    async def test_persist_failure_still_returns_ai_result(self):
        ai_result = MagicMock()
        ai_result.defect_class = "wear"
        ai_result.confidence = 0.8
        ai_result.rag_recommendation = ""
        ai_result.verdict = "monitor"

        with (
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.analyze_defect",
                AsyncMock(return_value=ai_result),
            ),
            patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc,
        ):
            svc.update_defect_ai_result = AsyncMock(side_effect=Exception("db error"))
            result = await run_ai_analysis(
                _make_defect_data(), defect_id="id-1", photo_bytes=[]
            )

        assert result is ai_result

    async def test_no_defect_class_skips_persist(self):
        ai_result = MagicMock()
        ai_result.defect_class = ""

        with (
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.analyze_defect",
                AsyncMock(return_value=ai_result),
            ),
            patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc,
        ):
            svc.update_defect_ai_result = AsyncMock()
            await run_ai_analysis(_make_defect_data(), defect_id="id-1", photo_bytes=[])

        svc.update_defect_ai_result.assert_not_awaited()


class TestNotifyDecommission:
    def _make_context(self):
        context = MagicMock()
        context.bot = AsyncMock()
        context.bot.send_message = AsyncMock()
        return context

    def _make_manager(self, tg_id, name="Manager"):
        m = MagicMock()
        m.telegram_id = tg_id
        m.full_name = name
        return m

    async def test_no_managers_sends_nothing(self):
        context = self._make_context()
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=[])
            await notify_decommission(
                context, employee=MagicMock(), defect=_make_defect_data()
            )
        context.bot.send_message.assert_not_awaited()

    async def test_sends_to_all_managers(self):
        context = self._make_context()
        managers = [self._make_manager(111), self._make_manager(222)]
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=managers)
            await notify_decommission(
                context, employee=MagicMock(), defect=_make_defect_data()
            )
        assert context.bot.send_message.await_count == 2

    async def test_sends_to_correct_chat_ids(self):
        context = self._make_context()
        managers = [self._make_manager(111), self._make_manager(222)]
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=managers)
            await notify_decommission(
                context, employee=MagicMock(), defect=_make_defect_data()
            )
        sent_ids = {
            call.kwargs["chat_id"] for call in context.bot.send_message.call_args_list
        }
        assert sent_ids == {111, 222}

    async def test_one_send_failure_does_not_block_others(self):
        context = self._make_context()
        context.bot.send_message = AsyncMock(side_effect=[Forbidden("blocked"), None])
        managers = [self._make_manager(111), self._make_manager(222)]
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=managers)
            await notify_decommission(
                context, employee=MagicMock(), defect=_make_defect_data()
            )
        assert context.bot.send_message.await_count == 2

    async def test_none_defect_does_not_raise(self):
        context = self._make_context()
        employee = MagicMock()
        employee.full_name = "Batbayar"
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(
                return_value=[self._make_manager(111)]
            )
            await notify_decommission(context, employee=employee, defect=None)
        context.bot.send_message.assert_awaited_once()
