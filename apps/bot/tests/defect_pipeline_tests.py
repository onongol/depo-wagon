import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.bot.fsm import load_defect
from apps.bot.handlers.defect.confirm.pipeline import (
    PersistResult,
    alert_decommission,
    persist_defect,
    register_defect,
    run_ai_analysis,
)
from apps.bot.handlers.defect.confirm.result import send_result
from apps.bot.handlers.defect.notifications import notify_decommission
from apps.bot.handlers.defect.text import (
    build_decommission_alert_text,
    build_recommendation_text,
    build_result_messages,
    build_result_text,
)
from apps.bot.keyboards.menu import main_menu_keyboard
from apps.bot.tests.builders import CHAT_ID, MESSAGE_ID, make_message
from apps.bot.user_data import AIResult, DefectData, MeasurementEntry, PhotoEntry
from apps.defects.constants import DefectVerdict

PIPELINE = "apps.bot.handlers.defect.confirm.pipeline"


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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
            svc.create_defect = AsyncMock(return_value=saved)
            result = await register_defect(
                _make_defect_data(), employee=MagicMock(), bot=bot
            )
        assert isinstance(result, PersistResult)
        assert result.defect is saved

    async def test_no_photos_returns_empty_photo_bytes(self):
        bot = AsyncMock()
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
            svc.create_defect = AsyncMock(return_value=_make_saved_defect())
            result = await register_defect(
                _make_defect_data(photo_file_ids=[]), employee=MagicMock(), bot=bot
            )
        assert result.photo_bytes == []
        svc.queue_defect_photos.assert_not_called()

    async def test_photos_are_queued_in_order_under_the_saved_defect(self):
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
            patch("apps.bot.handlers.defect.confirm.pipeline.register.services") as svc,
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.register._PHOTO_FETCH_TIMEOUT",
                0.05,
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.register.services"
        ) as svc:
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
                "apps.bot.handlers.defect.confirm.pipeline.analyze.analyze_defect",
                AsyncMock(return_value=ai_result),
            ),
            patch("apps.bot.handlers.defect.confirm.pipeline.analyze.services") as svc,
        ):
            svc.update_defect_ai_result = AsyncMock()
            result = await run_ai_analysis(
                _make_defect_data(), defect_id="id-1", photo_bytes=[b"img"]
            )

        assert result is ai_result

    async def test_analyze_exception_returns_none(self):
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.analyze.analyze_defect",
            AsyncMock(side_effect=Exception("model timeout")),
        ):
            result = await run_ai_analysis(
                _make_defect_data(), defect_id="id-1", photo_bytes=[]
            )

        assert result is None

    async def test_analyze_exception_never_raises(self):
        with patch(
            "apps.bot.handlers.defect.confirm.pipeline.analyze.analyze_defect",
            AsyncMock(side_effect=RuntimeError("crash")),
        ):
            await run_ai_analysis(_make_defect_data(), defect_id="id-1", photo_bytes=[])

    async def test_a_hung_analysis_times_out_to_none(self):
        """The confirm handler holds the user's lock for the whole call."""

        async def hang(**_):
            await asyncio.Event().wait()

        with (
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.analyze.analyze_defect", hang
            ),
            patch(
                "apps.bot.handlers.defect.confirm.pipeline.analyze._ANALYSIS_TIMEOUT",
                0.01,
            ),
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
                "apps.bot.handlers.defect.confirm.pipeline.analyze.analyze_defect",
                AsyncMock(return_value=ai_result),
            ),
            patch("apps.bot.handlers.defect.confirm.pipeline.analyze.services") as svc,
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
                "apps.bot.handlers.defect.confirm.pipeline.analyze.analyze_defect",
                AsyncMock(return_value=ai_result),
            ),
            patch("apps.bot.handlers.defect.confirm.pipeline.analyze.services") as svc,
        ):
            svc.update_defect_ai_result = AsyncMock()
            await run_ai_analysis(_make_defect_data(), defect_id="id-1", photo_bytes=[])

        svc.update_defect_ai_result.assert_not_awaited()


class TestPersistDefect:
    async def test_records_the_new_id_in_the_form(self, state, bot):
        form = _make_defect_data()
        saved = PersistResult(defect=_make_saved_defect("id-5"), photo_bytes=[])

        with patch(
            f"{PIPELINE}.persist.register_defect", AsyncMock(return_value=saved)
        ):
            result = await persist_defect(state, form, MagicMock(), bot)

        assert result is saved
        assert (await load_defect(state)).defect_id == "id-5"

    async def test_a_failed_save_raises_and_records_nothing(self, state, bot):
        failing = AsyncMock(side_effect=RuntimeError("db down"))

        with (
            patch(f"{PIPELINE}.persist.register_defect", failing),
            pytest.raises(RuntimeError),
        ):
            await persist_defect(state, _make_defect_data(), MagicMock(), bot)

        assert await load_defect(state) is None


class TestAlertDecommission:
    async def test_a_decommission_verdict_alerts(self):
        form = DefectData(verdict=DefectVerdict.DECOMMISSION)
        employee = MagicMock()

        with patch(f"{PIPELINE}.alert.notify_decommission", AsyncMock()) as notify:
            await alert_decommission(employee, form)

        notify.assert_awaited_once_with(employee, form)

    @pytest.mark.parametrize(
        "verdict", [DefectVerdict.OK, DefectVerdict.REPAIR_NOW, None]
    )
    async def test_any_other_verdict_does_not(self, verdict):
        with patch(f"{PIPELINE}.alert.notify_decommission", AsyncMock()) as notify:
            await alert_decommission(MagicMock(), DefectData(verdict=verdict))

        notify.assert_not_called()

    async def test_a_failed_alert_is_logged_not_raised(self, caplog):
        form = DefectData(verdict=DefectVerdict.DECOMMISSION, defect_id="id-5")
        failing = AsyncMock(side_effect=RuntimeError("broker down"))

        with patch(f"{PIPELINE}.alert.notify_decommission", failing):
            await alert_decommission(MagicMock(), form)

        assert "Decommission alert failed for id-5" in caplog.text


class TestSendResult:
    AI = AIResult(
        defect_class="Rim wear",
        confidence=0.8,
        verdict="repair_soon",
        rag_recommendation="Replace the pad",
    )

    async def test_one_message_with_the_menu_and_the_progress_goes(self, bot):
        progress = make_message()
        bot.delete_message = AsyncMock()

        await send_result(bot, progress, self.AI)

        (sent,) = progress.answer.await_args_list
        (expected,) = build_result_messages(self.AI)
        assert sent.kwargs["text"] == expected.render()[0]
        assert sent.kwargs["reply_markup"] == main_menu_keyboard()
        bot.delete_message.assert_awaited_once_with(
            chat_id=CHAT_ID, message_id=MESSAGE_ID
        )

    async def test_what_does_not_fit_follows_without_the_menu(self, bot):
        progress = make_message()
        bot.delete_message = AsyncMock()
        ai = self.AI.model_copy(update={"rag_recommendation": "x" * 4000})

        await send_result(bot, progress, ai)

        first, second = progress.answer.await_args_list
        assert first.kwargs["reply_markup"] == main_menu_keyboard()
        assert "reply_markup" not in second.kwargs


class TestNotifyDecommission:
    INSPECTOR = MagicMock(full_name="Batbayar")

    @pytest.fixture
    def svc(self):
        with patch("apps.bot.handlers.defect.notifications.services") as svc:
            svc.queue_messages = AsyncMock()
            yield svc

    async def test_no_managers_queues_nothing(self, svc):
        svc.get_managers_and_engineers = AsyncMock(return_value=[])

        await notify_decommission(self.INSPECTOR, _make_defect_data())

        svc.queue_messages.assert_not_called()

    async def test_queues_the_alert_for_every_manager(self, svc):
        managers = [MagicMock(id=7), MagicMock(id=9)]
        svc.get_managers_and_engineers = AsyncMock(return_value=managers)
        form = _make_defect_data()

        await notify_decommission(self.INSPECTOR, form)

        ids, text = svc.queue_messages.await_args.args
        assert ids == [7, 9]
        expected = build_decommission_alert_text(form, self.INSPECTOR)
        assert text.as_kwargs() == expected.as_kwargs()


class TestBuildDecommissionAlertText:
    INSPECTOR = MagicMock(full_name="Batbayar")

    def test_the_wagon_the_defect_and_who_found_it(self):
        text = build_decommission_alert_text(_make_defect_data(), self.INSPECTOR)

        assert text.as_html() == (
            "🔴 <b>Decommission Proposal</b>\n\n"
            "🚃 Wagon: 12345\n"
            "🔧 Node: Wheel\n"
            "⚠️ Defect: Crack\n"
            "👤 Inspector: Batbayar\n\n"
            "This wagon is recommended for decommission.\n"
            "Please review in App."
        )

    def test_a_missing_label_is_a_dash(self):
        text = build_decommission_alert_text(DefectData(), self.INSPECTOR)

        assert "🚃 Wagon: —\n🔧 Node: —\n⚠️ Defect: —\n" in text.as_html()

    def test_markup_in_the_values_stays_text(self):
        form = _make_defect_data(wagon_number="<b>1</b>")
        inspector = MagicMock(full_name="A & <B>")

        rendered, entities = build_decommission_alert_text(form, inspector).render()

        assert "Wagon: <b>1</b>" in rendered
        assert "Inspector: A & <B>" in rendered
        assert [e.type for e in entities] == ["bold"]


class TestBuildResultText:
    AI = AIResult(defect_class="Rim wear", confidence=0.8, verdict="repair_soon")

    def test_the_saved_defect_then_the_analysis(self):
        text = build_result_text(self.AI)

        assert text.as_html() == (
            "✅ <b>Defect registered successfully!</b>\n\n"
            "🤖 <b>AI Analysis:</b>\n"
            "📌 Rim wear\n"
            "📊 Confidence: 80%\n"
            "🟡 AI verdict: <code>Repair Soon</code>"
        )

    def test_without_the_ai_it_says_so(self):
        rendered = build_result_text(None).render()[0]

        assert rendered == (
            "✅ Defect registered successfully!\n\nℹ️ AI analysis is not available."
        )

    def test_the_ai_class_is_sent_as_it_came(self):
        ai = self.AI.model_copy(update={"defect_class": "Wear <5 mm> & chips"})

        assert "📌 Wear <5 mm> & chips" in build_result_text(ai).render()[0]


class TestBuildRecommendationText:
    def test_none_without_a_recommendation(self):
        assert build_recommendation_text(None) is None
        assert build_recommendation_text(AIResult()) is None

    def test_the_sources_follow_it(self):
        ai = AIResult(
            rag_recommendation="Replace <the> pad", sources=["Doc 1", "Doc 2"]
        )

        rendered = build_recommendation_text(ai).render()[0]

        assert rendered == (
            "💡 Recommendation:\nReplace <the> pad\n\n📎 Sources:\nDoc 1\nDoc 2"
        )

    def test_it_is_quoted_under_its_label(self):
        ai = AIResult(rag_recommendation="Replace the pad")

        assert build_recommendation_text(ai).as_html() == (
            "💡 <b>Recommendation:</b>\n"
            "<blockquote expandable>Replace the pad</blockquote>"
        )

    @pytest.mark.parametrize("char", ["x", "🔧"], ids=["ascii", "emoji"])
    def test_one_past_the_cap_is_cut_short_and_keeps_its_sources(self, char):
        ai = AIResult(rag_recommendation=char * 5000, sources=["Doc 1"])

        rendered = build_recommendation_text(ai).render()[0]

        # A split emoji is dropped whole, so one unit may go unused
        assert 4095 <= len(rendered.encode("utf-16-le")) // 2 <= 4096
        assert rendered.endswith(f"{char}…\n\n📎 Sources:\nDoc 1")


class TestBuildResultMessages:
    AI = AIResult(defect_class="Rim wear", confidence=0.8, verdict="repair_soon")

    def _rendered(self, ai):
        return [text.render()[0] for text in build_result_messages(ai)]

    def test_without_a_recommendation_the_result_alone(self):
        assert self._rendered(self.AI) == [build_result_text(self.AI).render()[0]]

    def test_a_recommendation_joins_the_result(self):
        ai = self.AI.model_copy(update={"rag_recommendation": "Replace the pad"})

        (message,) = self._rendered(ai)

        assert message == (
            build_result_text(ai).render()[0]
            + "\n\n"
            + build_recommendation_text(ai).render()[0]
        )

    def test_together_past_the_cap_they_go_apart(self):
        ai = self.AI.model_copy(update={"rag_recommendation": "x" * 4000})

        assert self._rendered(ai) == [
            build_result_text(ai).render()[0],
            build_recommendation_text(ai).render()[0],
        ]

    def test_emoji_count_twice_toward_the_cap(self):
        """Together they fit by len(), not in the UTF-16 units Telegram counts."""
        result = build_result_text(self.AI).render()[0]
        heading = "💡 Recommendation:\n"
        spare = 4096 - len(result) - len("\n\n") - len(heading)
        emoji = "🔧" * 10
        recommendation = "x" * (spare - len(emoji)) + emoji
        ai = self.AI.model_copy(update={"rag_recommendation": recommendation})

        messages = self._rendered(ai)

        assert len(messages) == 2
        assert messages[1].endswith(emoji)
