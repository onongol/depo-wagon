from unittest.mock import AsyncMock, MagicMock, patch

from telegram.ext import ConversationHandler

from apps.bot.constants import UD_DEFECT, UD_EMPLOYEE, UD_REG
from apps.bot.handlers.common.cancel import cancel
from apps.bot.handlers.common.help import help_command
from apps.bot.handlers.common.start import start
from apps.bot.messages import BotMessages as M
from apps.bot.states import AUTH_EMAIL


class TestCancelHandler:
    async def test_clears_reg_and_defect_data(self, mock_update, mock_context):
        mock_context.user_data[UD_REG] = {"email": "test@depot.mn"}
        mock_context.user_data[UD_DEFECT] = {"node": "wheel"}

        await cancel(mock_update, mock_context)

        assert UD_REG not in mock_context.user_data
        assert UD_DEFECT not in mock_context.user_data

    async def test_replies_with_cancelled_message(self, mock_update, mock_context):
        await cancel(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            str(M.CANCELLED), parse_mode=M.PARSE_MODE
        )

    async def test_returns_conversation_end(self, mock_update, mock_context):
        result = await cancel(mock_update, mock_context)
        assert result == ConversationHandler.END

    async def test_tolerates_empty_user_data(self, mock_update, mock_context):
        await cancel(mock_update, mock_context)
        assert UD_REG not in mock_context.user_data
        assert UD_DEFECT not in mock_context.user_data


class TestHelpHandler:
    async def test_replies_with_help_text(self, mock_update, mock_context):
        await help_command(mock_update, mock_context)

        mock_update.message.reply_text.assert_called_once_with(
            str(M.HELP_TEXT), parse_mode=M.PARSE_MODE
        )


class TestStartHandler:
    def _make_employee(self):
        employee = MagicMock()
        employee.full_name = "Батбаяр Дорж"
        employee.get_role_display.return_value = "Инспектор"
        employee.role = "inspector"
        return employee

    async def test_known_employee_saves_to_user_data(self, mock_update, mock_context):
        employee = self._make_employee()
        with patch("apps.bot.handlers.common.start.services") as mock_services:
            mock_services.get_employee_by_telegram_id = AsyncMock(return_value=employee)
            await start(mock_update, mock_context)

        assert mock_context.user_data[UD_EMPLOYEE] is employee

    async def test_known_employee_returns_end(self, mock_update, mock_context):
        employee = self._make_employee()
        with patch("apps.bot.handlers.common.start.services") as mock_services:
            mock_services.get_employee_by_telegram_id = AsyncMock(return_value=employee)
            result = await start(mock_update, mock_context)

        assert result == ConversationHandler.END

    async def test_new_user_returns_auth_email(self, mock_update, mock_context):
        with patch("apps.bot.handlers.common.start.services") as mock_services:
            mock_services.get_employee_by_telegram_id = AsyncMock(return_value=None)
            result = await start(mock_update, mock_context)

        assert result == AUTH_EMAIL

    async def test_new_user_clears_stale_reg_data(self, mock_update, mock_context):
        mock_context.user_data[UD_REG] = {"leftover": True}
        with patch("apps.bot.handlers.common.start.services") as mock_services:
            mock_services.get_employee_by_telegram_id = AsyncMock(return_value=None)
            await start(mock_update, mock_context)

        assert UD_REG not in mock_context.user_data

    async def test_uses_telegram_id_from_update(self, mock_update, mock_context):
        mock_update.effective_user.id = 99999
        with patch("apps.bot.handlers.common.start.services") as mock_services:
            mock_services.get_employee_by_telegram_id = AsyncMock(return_value=None)
            await start(mock_update, mock_context)

        mock_services.get_employee_by_telegram_id.assert_called_once_with(99999)
