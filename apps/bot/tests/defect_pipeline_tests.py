import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramForbiddenError

from apps.bot.handlers.defect.confirm.pipeline import (
    PersistResult,
    register_defect,
    run_ai_analysis,
)
from apps.bot.handlers.defect.notifications import notify_decommission
from apps.bot.user_data import DefectData, MeasurementEntry, PhotoEntry


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
        photos=[
            PhotoEntry(file_id=file_id, message_id=i)
            for i, file_id in enumerate(kwargs.get("photo_file_ids", []))
        ],
        measurements=kwargs.get("measurements", []),
    )
    return data


def _make_saved_defect(defect_id="uuid-001"):
    defect = MagicMock()
    defect.id = defect_id
    return defect


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
        svc.queue_defect_photos.assert_not_called()

    async def test_photos_are_queued_in_order_under_the_saved_defect(self):
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect("id-7"))
            svc.queue_defect_photos = AsyncMock()
            svc.download_photo = AsyncMock(return_value=b"img")
            await register_defect(
                _make_defect_data(photo_file_ids=["a", "b", "c"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        svc.queue_defect_photos.assert_awaited_once_with("id-7", ["a", "b", "c"])

    async def test_queueing_failure_is_non_critical(self):
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.queue_defect_photos = AsyncMock(side_effect=Exception("broker down"))
            svc.download_photo = AsyncMock(return_value=b"img")
            result = await register_defect(
                _make_defect_data(photo_file_ids=["file123"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        assert result.photo_bytes == [b"img"]

    async def test_photo_downloaded_and_returned(self):
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.queue_defect_photos = AsyncMock()
            svc.download_photo = AsyncMock(return_value=b"img")
            result = await register_defect(
                _make_defect_data(photo_file_ids=["file123"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        assert result.photo_bytes == [b"img"]

    async def test_photo_download_failure_is_non_critical(self):
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.queue_defect_photos = AsyncMock()
            svc.download_photo = AsyncMock(side_effect=Exception("Telegram timeout"))
            result = await register_defect(
                _make_defect_data(photo_file_ids=["file123"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        assert result.photo_bytes == []

    async def test_oversized_photo_is_skipped(self):
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.queue_defect_photos = AsyncMock()
            svc.download_photo = AsyncMock(return_value=None)
            result = await register_defect(
                _make_defect_data(photo_file_ids=["big_file"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        assert result.photo_bytes == []

    async def test_one_photo_fail_does_not_block_others(self):
        with patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.queue_defect_photos = AsyncMock()
            svc.download_photo = AsyncMock(
                side_effect=[Exception("network error"), b"ok"]
            )
            result = await register_defect(
                _make_defect_data(photo_file_ids=["bad", "good"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        assert result.photo_bytes == [b"ok"]

    async def test_a_photo_slower_than_the_budget_is_left_out_of_the_analysis(self):
        async def download(bot, file_id):
            if file_id == "slow":
                await asyncio.sleep(1)
            return file_id.encode()

        with (
            patch("apps.bot.handlers.defect.confirm.pipeline.services") as svc,
            patch(
                "apps.bot.handlers.defect.confirm.pipeline._PHOTO_FETCH_TIMEOUT", 0.05
            ),
        ):
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            svc.queue_defect_photos = AsyncMock()
            svc.download_photo = download
            result = await register_defect(
                _make_defect_data(photo_file_ids=["slow", "fast"]),
                employee=MagicMock(),
                bot=AsyncMock(),
            )
        assert result.photo_bytes == [b"fast"]
        svc.queue_defect_photos.assert_awaited_once_with("uuid-001", ["slow", "fast"])

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

    async def test_a_hung_analysis_times_out_to_none(self):
        """The confirm handler holds the user's lock for the whole call."""

        async def hang(**_):
            await asyncio.Event().wait()

        with (
            patch("apps.bot.handlers.defect.confirm.pipeline.analyze_defect", hang),
            patch("apps.bot.handlers.defect.confirm.pipeline._ANALYSIS_TIMEOUT", 0.01),
        ):
            result = await run_ai_analysis(
                _make_defect_data(), defect_id="id-1", photo_bytes=[]
            )

        assert result is None

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
                context.bot, employee=MagicMock(), defect=_make_defect_data()
            )
        context.bot.send_message.assert_not_awaited()

    async def test_sends_to_all_managers(self):
        context = self._make_context()
        managers = [self._make_manager(111), self._make_manager(222)]
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=managers)
            await notify_decommission(
                context.bot, employee=MagicMock(), defect=_make_defect_data()
            )
        assert context.bot.send_message.await_count == 2

    async def test_sends_to_correct_chat_ids(self):
        context = self._make_context()
        managers = [self._make_manager(111), self._make_manager(222)]
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=managers)
            await notify_decommission(
                context.bot, employee=MagicMock(), defect=_make_defect_data()
            )
        sent_ids = {
            call.kwargs["chat_id"] for call in context.bot.send_message.call_args_list
        }
        assert sent_ids == {111, 222}

    async def test_one_send_failure_does_not_block_others(self):
        context = self._make_context()
        context.bot.send_message = AsyncMock(
            side_effect=[TelegramForbiddenError(method=None, message="blocked"), None]
        )
        managers = [self._make_manager(111), self._make_manager(222)]
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.get_managers_and_engineers = AsyncMock(return_value=managers)
            await notify_decommission(
                context.bot, employee=MagicMock(), defect=_make_defect_data()
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
            await notify_decommission(context.bot, employee=employee, defect=None)
        context.bot.send_message.assert_awaited_once()
