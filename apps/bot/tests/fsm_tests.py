"""Tests for the aiogram FSM layer.

These use a real FSMContext over MemoryStorage rather than a mock, so
get_state and get_data behave exactly as they will against Redis.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from redis.asyncio.connection import Connection
from redis.exceptions import ConnectionError as RedisConnectionError

from apps.bot.constants import (
    UD_AI_CHAT_HISTORY,
    UD_DEFECT,
    UD_EDITING,
    UD_RESP_SEARCH,
)
from apps.bot.fsm import clear_defect_keys, load_defect, save_defect
from apps.bot.fsm.storage import (
    FSM_LOCK_TIMEOUT,
    FSM_RETRIES,
    FSM_SOCKET_TIMEOUT,
    FSM_TTL,
)
from apps.bot.handlers.ai_chat.receive import _ANSWER_TIMEOUT
from apps.bot.handlers.defect.confirm.pipeline import _ANALYSIS_TIMEOUT
from apps.bot.user_data import DefectData, MeasurementEntry


@pytest.fixture
def state() -> FSMContext:
    return FSMContext(
        storage=MemoryStorage(),
        key=StorageKey(bot_id=42, chat_id=12345, user_id=12345),
    )


class TestLoadAndSaveDefect:
    async def test_returns_none_when_the_flow_is_not_running(self, state):
        assert await load_defect(state) is None

    async def test_round_trips_a_populated_form(self, state):
        defect = DefectData(
            wagon_number="60123456",
            department="coupler_brake",
            measurements=[MeasurementEntry(dimension="thickness", value=12.5)],
            photo_file_ids=["a", "b"],
        )

        await save_defect(state, defect)

        assert await load_defect(state) == defect

    async def test_rebuilds_nested_entries_as_models(self, state):
        await save_defect(
            state,
            DefectData(current_measurement=MeasurementEntry(dimension="width")),
        )

        restored = await load_defect(state)

        assert isinstance(restored.current_measurement, MeasurementEntry)

    async def test_saving_replaces_rather_than_merges(self, state):
        await save_defect(state, DefectData(photo_file_ids=["a", "b"]))
        await save_defect(state, DefectData(photo_file_ids=["c"]))

        assert (await load_defect(state)).photo_file_ids == ["c"]

    async def test_a_loaded_copy_is_detached_until_saved(self, state):
        await save_defect(state, DefectData(wagon_number="1"))

        stale = await load_defect(state)
        stale.wagon_number = "2"

        assert (await load_defect(state)).wagon_number == "1"

    async def test_saving_leaves_unrelated_keys_alone(self, state):
        await state.update_data({UD_AI_CHAT_HISTORY: [{"q": "a"}]})

        await save_defect(state, DefectData())

        assert (await state.get_data())[UD_AI_CHAT_HISTORY] == [{"q": "a"}]


class TestClearDefectKeys:
    async def test_drops_every_key_the_defect_flow_owns(self, state):
        await state.update_data(
            {
                UD_DEFECT: DefectData().to_dict(),
                UD_RESP_SEARCH: "query",
                UD_EDITING: True,
            }
        )

        await clear_defect_keys(state)

        assert await state.get_data() == {}

    async def test_keeps_the_ai_chat_history(self, state):
        await state.update_data(
            {UD_DEFECT: DefectData().to_dict(), UD_AI_CHAT_HISTORY: [{"q": "a"}]}
        )

        await clear_defect_keys(state)

        assert await state.get_data() == {UD_AI_CHAT_HISTORY: [{"q": "a"}]}

    async def test_is_a_no_op_when_nothing_is_stored(self, state):
        await clear_defect_keys(state)

        assert await state.get_data() == {}

    async def test_leaves_the_state_itself_untouched(self, state):
        await state.set_state("DefectSG:photo")
        await state.update_data({UD_DEFECT: DefectData().to_dict()})

        await clear_defect_keys(state)

        assert await state.get_state() == "DefectSG:photo"


class TestStorageTtl:
    def test_expiry_is_set_so_abandoned_forms_do_not_accumulate(self):
        assert timedelta(days=1) == FSM_TTL


class TestMakeStorage:
    """Configuration only — Redis.from_url does not connect until first use."""

    def test_uses_the_dedicated_fsm_url_not_the_django_cache(self, settings):
        from apps.bot.fsm.storage import make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"
        settings.REDIS_URL = "redis://localhost:6379/0"

        storage = make_storage()

        assert storage.redis.connection_pool.connection_kwargs["db"] == 9

    def test_applies_the_ttl_to_both_state_and_data(self, settings):
        from apps.bot.fsm.storage import make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"

        storage = make_storage()

        assert storage.state_ttl == FSM_TTL
        assert storage.data_ttl == FSM_TTL

    def test_sets_the_socket_timeouts_explicitly(self, settings):
        from apps.bot.fsm.storage import make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"

        kwargs = make_storage().redis.connection_pool.connection_kwargs

        assert kwargs["socket_timeout"] == FSM_SOCKET_TIMEOUT
        assert kwargs["socket_connect_timeout"] == FSM_SOCKET_TIMEOUT

    def test_the_retry_reaches_the_pool_connections(self, settings):
        from apps.bot.fsm.storage import make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"

        conn = make_storage().redis.connection_pool.make_connection()

        assert conn.retry.get_retries() == FSM_RETRIES

    def test_keys_include_the_bot_id_so_staging_cannot_collide(self, settings):
        from apps.bot.fsm.storage import make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"

        storage = make_storage()
        key = StorageKey(bot_id=42, chat_id=1, user_id=1)

        assert "42" in storage.key_builder.build(key, "state")


class TestMakeIsolation:
    def test_locks_over_the_storage_connection_and_keys(self, settings):
        from apps.bot.fsm.storage import make_isolation, make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"
        storage = make_storage()

        isolation = make_isolation(storage)

        assert isolation.redis is storage.redis
        assert isolation.key_builder is storage.key_builder
        assert isolation.lock_kwargs == {"timeout": FSM_LOCK_TIMEOUT}

    def test_a_lock_outlives_the_slowest_ai_call(self):
        """Whole handlers run under it, AI calls included."""
        assert max(_ANSWER_TIMEOUT, _ANALYSIS_TIMEOUT) < FSM_LOCK_TIMEOUT


class TestRedisOutage:
    async def test_a_refused_connection_is_retried_before_giving_up(self, settings):
        from apps.bot.fsm.storage import make_storage

        settings.TELEGRAM_FSM_REDIS_URL = "redis://localhost:6379/9"
        storage = make_storage()
        refused = AsyncMock(side_effect=ConnectionRefusedError(61, "refused"))

        with (
            patch.object(Connection, "_connect", refused),
            pytest.raises(RedisConnectionError),
        ):
            await storage.get_state(StorageKey(bot_id=42, chat_id=1, user_id=1))

        assert refused.await_count == FSM_RETRIES + 1
