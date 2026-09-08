from unittest.mock import AsyncMock, patch

from telegram.ext import Application, CallbackQueryHandler, InvalidCallbackData

from apps.bot.application import _BotApplication, create_application
from apps.bot.callbacks import LinkCancelCB, LinkConfirmCB


class TestBotApplication:
    async def test_calls_close_old_connections_before_super(self):
        update = object()
        call_order = []

        with (
            patch(
                "apps.bot.application.close_old_connections",
                side_effect=lambda: call_order.append("close"),
            ),
            patch.object(
                Application,
                "process_update",
                new_callable=AsyncMock,
                side_effect=lambda u: call_order.append("super"),
            ),
        ):
            instance = object.__new__(_BotApplication)
            await _BotApplication.process_update(instance, update)

        assert call_order == ["close", "super"]

    async def test_passes_update_to_super(self):
        update = object()
        with (
            patch("apps.bot.application.close_old_connections"),
            patch.object(
                Application, "process_update", new_callable=AsyncMock
            ) as mock_super,
        ):
            instance = object.__new__(_BotApplication)
            await _BotApplication.process_update(instance, update)

        mock_super.assert_called_once_with(update)


def _callback_handlers(app):
    return [h for h in app.handlers[0] if isinstance(h, CallbackQueryHandler)]


def _predicate_patterns(app):
    """Patterns PTB calls to decide a match, which excludes bare types."""
    return [
        h.pattern
        for h in _callback_handlers(app)
        if callable(h.pattern) and not isinstance(h.pattern, type)
    ]


class TestCallbackHandlersAreRegistered:
    """Handler tests call the callbacks directly; only this proves they are wired."""

    def test_link_callbacks_reach_a_handler(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "123456:ABCdefGHI"
        app = create_application()

        patterns = _predicate_patterns(app)

        assert any(p(LinkConfirmCB(employee_id=1)) for p in patterns)
        assert any(p(LinkCancelCB()) for p in patterns)

    def test_expired_buttons_reach_a_handler(self, settings):
        settings.TELEGRAM_BOT_TOKEN = "123456:ABCdefGHI"
        app = create_application()

        assert any(h.pattern is InvalidCallbackData for h in _callback_handlers(app))

    def test_the_expired_button_handler_goes_last(self, settings):
        """Anything registered after it would never see a typed callback."""
        settings.TELEGRAM_BOT_TOKEN = "123456:ABCdefGHI"
        app = create_application()

        handlers = _callback_handlers(app)
        catch_all = next(h for h in handlers if h.pattern is InvalidCallbackData)

        assert handlers.index(catch_all) == len(handlers) - 1


class TestDefectStatesRouteEachCallbackToOneHandler:
    """The split handlers replace an isinstance chain; routing has to be exact."""

    def _handlers_for(self, state, cb):
        from apps.bot.handlers.defect.conversation import get_defect_handler

        return [
            h
            for h in get_defect_handler().states[state]
            if isinstance(h, CallbackQueryHandler) and h.pattern(cb)
        ]

    def test_each_responsible_employee_callback_has_exactly_one_handler(self):
        from apps.bot.callbacks import (
            ResponsibleEmployeeCB,
            ResponsibleEmployeePageCB,
            ResponsibleEmployeeSkipCB,
        )
        from apps.bot.states import RESPONSIBLE_EMPLOYEE

        for cb, expected in (
            (ResponsibleEmployeeCB(employee_id=1), "select_responsible_employee"),
            (ResponsibleEmployeeSkipCB(), "skip_responsible_employee"),
            (ResponsibleEmployeePageCB(page=0), "page_responsible_employee"),
        ):
            matched = self._handlers_for(RESPONSIBLE_EMPLOYEE, cb)
            assert len(matched) == 1, cb
            assert matched[0].callback.__name__ == expected

    def test_each_measurement_choice_callback_has_exactly_one_handler(self):
        from apps.bot.callbacks import (
            MeasurementAddCB,
            MeasurementDoneCB,
            MeasurementSkipCB,
        )
        from apps.bot.states import MEASUREMENT_CHOICE

        for cb, expected in (
            (MeasurementAddCB(), "measurement_add"),
            (MeasurementSkipCB(), "measurement_done"),
            (MeasurementDoneCB(), "measurement_done"),
        ):
            matched = self._handlers_for(MEASUREMENT_CHOICE, cb)
            assert len(matched) == 1, cb
            assert matched[0].callback.__name__ == expected

    def test_a_foreign_callback_matches_nothing_in_those_states(self):
        from apps.bot.callbacks import DepartmentCB
        from apps.bot.states import MEASUREMENT_CHOICE, RESPONSIBLE_EMPLOYEE

        for state in (RESPONSIBLE_EMPLOYEE, MEASUREMENT_CHOICE):
            assert self._handlers_for(state, DepartmentCB(value="bogie")) == []
