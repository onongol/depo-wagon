from unittest.mock import AsyncMock, MagicMock, patch

from telegram.ext import ConversationHandler

from apps.bot.constants import UD_EMPLOYEE, UD_REG, OtpStatus, RegStatus
from apps.bot.handlers.common.email import receive_email
from apps.bot.handlers.common.otp import receive_otp
from apps.bot.states import AUTH_EMAIL, AUTH_OTP
from apps.bot.user_data import RegData


def _make_update(text, user_id=12345):
    update = MagicMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.effective_user.id = user_id
    return update


def _make_employee(**kwargs):
    emp = MagicMock()
    emp.id = kwargs.get("id", 1)
    emp.first_name = kwargs.get("first_name", "Бат")
    emp.full_name = kwargs.get("full_name", "Батбаяр Дорж")
    emp.get_role_display.return_value = kwargs.get("role_display", "Инспектор")
    return emp


class TestReceiveEmail:
    async def test_invalid_format_stays_on_auth_email(self, mock_context):
        update = _make_update("notanemail")
        result = await receive_email(update, mock_context)
        assert result == AUTH_EMAIL

    async def test_invalid_format_replies(self, mock_context):
        update = _make_update("bad@@email")
        await receive_email(update, mock_context)
        update.message.reply_text.assert_called_once()

    async def test_not_found_stays_on_auth_email(self, mock_context):
        update = _make_update("unknown@depot.mn")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(None, "not_found"))
            result = await receive_email(update, mock_context)
        assert result == AUTH_EMAIL

    async def test_already_linked_returns_end(self, mock_context):
        update = _make_update("linked@depot.mn")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(None, "already_linked"))
            result = await receive_email(update, mock_context)
        assert result == ConversationHandler.END

    async def test_otp_generation_exception_stays_on_auth_email(self, mock_context):
        update = _make_update("user@depot.mn")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(_make_employee(), "ok"))
            svc.generate_and_store_otp = AsyncMock(side_effect=Exception("redis down"))
            result = await receive_email(update, mock_context)
        assert result == AUTH_EMAIL

    async def test_otp_not_delivered_stays_on_auth_email(self, mock_context):
        update = _make_update("user@depot.mn")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(_make_employee(), "ok"))
            svc.generate_and_store_otp = AsyncMock(return_value="123456")
            svc.send_otp_email = AsyncMock(return_value=False)
            result = await receive_email(update, mock_context)
        assert result == AUTH_EMAIL

    async def test_success_returns_auth_otp(self, mock_context):
        update = _make_update("user@depot.mn")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(_make_employee(), "ok"))
            svc.generate_and_store_otp = AsyncMock(return_value="123456")
            svc.send_otp_email = AsyncMock(return_value=True)
            result = await receive_email(update, mock_context)
        assert result == AUTH_OTP

    async def test_success_stores_reg_data(self, mock_context):
        update = _make_update("user@depot.mn")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(_make_employee(), "ok"))
            svc.generate_and_store_otp = AsyncMock(return_value="123456")
            svc.send_otp_email = AsyncMock(return_value=True)
            await receive_email(update, mock_context)
        reg: RegData = mock_context.user_data.get(UD_REG)
        assert isinstance(reg, RegData)
        assert reg.email == "user@depot.mn"

    async def test_email_is_stripped_before_lookup(self, mock_context):
        update = _make_update("  user@depot.mn  ")
        with patch("apps.bot.handlers.common.email.services") as svc:
            svc.get_employee_for_auth = AsyncMock(return_value=(_make_employee(), "ok"))
            svc.generate_and_store_otp = AsyncMock(return_value="123456")
            svc.send_otp_email = AsyncMock(return_value=True)
            await receive_email(update, mock_context)
        called_email = svc.get_employee_for_auth.call_args[0][0]
        assert called_email == "user@depot.mn"


class TestReceiveOtp:
    async def test_no_session_returns_end(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        result = await receive_otp(mock_update, mock_context)
        assert result == ConversationHandler.END

    async def test_no_session_replies(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        await receive_otp(mock_update, mock_context)
        mock_update.message.reply_text.assert_called_once()

    async def test_expired_otp_returns_auth_email(self, mock_update, mock_context):
        mock_update.message.text = "000000"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with patch("apps.bot.handlers.common.otp.services") as svc:
            svc.verify_otp = AsyncMock(return_value=(None, OtpStatus.EXPIRED))
            result = await receive_otp(mock_update, mock_context)
        assert result == AUTH_EMAIL
        assert UD_REG not in mock_context.user_data

    async def test_max_attempts_returns_auth_email(self, mock_update, mock_context):
        mock_update.message.text = "000000"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with patch("apps.bot.handlers.common.otp.services") as svc:
            svc.verify_otp = AsyncMock(return_value=(None, OtpStatus.MAX_ATTEMPTS))
            result = await receive_otp(mock_update, mock_context)
        assert result == AUTH_EMAIL
        assert UD_REG not in mock_context.user_data

    async def test_wrong_code_stays_on_auth_otp(self, mock_update, mock_context):
        mock_update.message.text = "000000"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with patch("apps.bot.handlers.common.otp.services") as svc:
            svc.verify_otp = AsyncMock(return_value=(None, OtpStatus.WRONG))
            result = await receive_otp(mock_update, mock_context)
        assert result == AUTH_OTP

    async def test_wrong_code_preserves_session(self, mock_update, mock_context):
        mock_update.message.text = "000000"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with patch("apps.bot.handlers.common.otp.services") as svc:
            svc.verify_otp = AsyncMock(return_value=(None, OtpStatus.WRONG))
            await receive_otp(mock_update, mock_context)
        assert UD_REG in mock_context.user_data

    async def test_service_exception_returns_end(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with patch("apps.bot.handlers.common.otp.services") as svc:
            svc.verify_otp = AsyncMock(return_value=(1, OtpStatus.OK))
            svc.get_employee_by_id = AsyncMock(side_effect=Exception("db error"))
            result = await receive_otp(mock_update, mock_context)
        assert result == ConversationHandler.END

    async def test_created_sends_credentials_email(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with (
            patch("apps.bot.handlers.common.otp.services") as svc,
            patch(
                "apps.bot.handlers.common.otp.show_welcome_menu", new_callable=AsyncMock
            ),
        ):
            svc.verify_otp = AsyncMock(return_value=(1, OtpStatus.OK))
            svc.get_employee_by_id = AsyncMock(return_value=_make_employee())
            svc.register_employee = AsyncMock(
                return_value=("secret123", RegStatus.CREATED)
            )
            svc.send_credentials_email = AsyncMock()
            await receive_otp(mock_update, mock_context)
        svc.send_credentials_email.assert_awaited_once()

    async def test_created_returns_end(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with (
            patch("apps.bot.handlers.common.otp.services") as svc,
            patch(
                "apps.bot.handlers.common.otp.show_welcome_menu", new_callable=AsyncMock
            ),
        ):
            svc.verify_otp = AsyncMock(return_value=(1, OtpStatus.OK))
            svc.get_employee_by_id = AsyncMock(return_value=_make_employee())
            svc.register_employee = AsyncMock(
                return_value=("secret", RegStatus.CREATED)
            )
            svc.send_credentials_email = AsyncMock()
            result = await receive_otp(mock_update, mock_context)
        assert result == ConversationHandler.END

    async def test_linked_skips_credentials_email(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with (
            patch("apps.bot.handlers.common.otp.services") as svc,
            patch(
                "apps.bot.handlers.common.otp.show_welcome_menu", new_callable=AsyncMock
            ),
        ):
            svc.verify_otp = AsyncMock(return_value=(1, OtpStatus.OK))
            svc.get_employee_by_id = AsyncMock(return_value=_make_employee())
            svc.register_employee = AsyncMock(return_value=(None, RegStatus.LINKED))
            svc.send_credentials_email = AsyncMock()
            await receive_otp(mock_update, mock_context)
        svc.send_credentials_email.assert_not_awaited()

    async def test_success_saves_employee_to_user_data(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        employee = _make_employee()
        with (
            patch("apps.bot.handlers.common.otp.services") as svc,
            patch(
                "apps.bot.handlers.common.otp.show_welcome_menu", new_callable=AsyncMock
            ),
        ):
            svc.verify_otp = AsyncMock(return_value=(1, OtpStatus.OK))
            svc.get_employee_by_id = AsyncMock(return_value=employee)
            svc.register_employee = AsyncMock(return_value=(None, RegStatus.LINKED))
            await receive_otp(mock_update, mock_context)
        assert mock_context.user_data[UD_EMPLOYEE] is employee

    async def test_success_clears_reg_data(self, mock_update, mock_context):
        mock_update.message.text = "123456"
        mock_context.user_data[UD_REG] = RegData(email="user@depot.mn")
        with (
            patch("apps.bot.handlers.common.otp.services") as svc,
            patch(
                "apps.bot.handlers.common.otp.show_welcome_menu", new_callable=AsyncMock
            ),
        ):
            svc.verify_otp = AsyncMock(return_value=(1, OtpStatus.OK))
            svc.get_employee_by_id = AsyncMock(return_value=_make_employee())
            svc.register_employee = AsyncMock(return_value=(None, RegStatus.LINKED))
            await receive_otp(mock_update, mock_context)
        assert UD_REG not in mock_context.user_data
