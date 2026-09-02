from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail

from apps.users.notifications import (
    CONNECTED,
    DISCONNECTED,
    notify_telegram_link_change,
    send_telegram_link_email,
)
from apps.users.tasks import send_telegram_link_notification

User = get_user_model()


@pytest.fixture
def owner(db):
    user = User.objects.create_user(email="owner@depot.mn", password="pass12345")
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    return user


@pytest.mark.django_db
class TestSendTelegramLinkEmail:
    @pytest.mark.parametrize("action", [CONNECTED, DISCONNECTED])
    def test_goes_to_the_primary_address(self, owner, action):
        assert send_telegram_link_email(owner, action) is True
        assert mail.outbox[0].to == ["owner@depot.mn"]

    def test_subject_carries_the_project_prefix(self, owner, settings):
        settings.ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Depo Wagon] "
        send_telegram_link_email(owner, CONNECTED)
        assert mail.outbox[0].subject.startswith("[Depo Wagon] ")

    def test_the_two_actions_read_differently(self, owner):
        send_telegram_link_email(owner, CONNECTED)
        send_telegram_link_email(owner, DISCONNECTED)
        assert mail.outbox[0].subject != mail.outbox[1].subject
        assert mail.outbox[0].body != mail.outbox[1].body

    def test_body_links_to_the_telegram_page(self, owner, settings):
        settings.SITE_URL = "https://depowagon.mn/"
        send_telegram_link_email(owner, CONNECTED)
        assert "https://depowagon.mn/telegram/" in mail.outbox[0].body

    def test_falls_back_to_the_account_email_when_unconfirmed(self, db):
        user = User.objects.create_user(email="new@depot.mn", password="pass12345")
        assert send_telegram_link_email(user, CONNECTED) is True
        assert mail.outbox[0].to == ["new@depot.mn"]

    def test_a_user_with_no_address_at_all_gets_nothing(self, db):
        user = User.objects.create_user(email="none@depot.mn", password="pass12345")
        user.email = ""
        assert send_telegram_link_email(user, CONNECTED) is False
        assert mail.outbox == []

    def test_project_wide_notification_switch_is_honoured(self, owner, settings):
        settings.ACCOUNT_EMAIL_NOTIFICATIONS = False
        assert send_telegram_link_email(owner, CONNECTED) is False
        assert mail.outbox == []


@pytest.mark.django_db
class TestNotifyTelegramLinkChange:
    def test_queues_the_task(self, owner):
        with patch("apps.users.tasks.send_telegram_link_notification.delay") as delay:
            notify_telegram_link_change(owner.pk, CONNECTED)
        delay.assert_called_once_with(owner.pk, CONNECTED)

    def test_a_dead_broker_does_not_propagate(self, owner):
        with patch(
            "apps.users.tasks.send_telegram_link_notification.delay",
            side_effect=Exception("broker is down"),
        ):
            notify_telegram_link_change(owner.pk, CONNECTED)


@pytest.mark.django_db
class TestSendTelegramLinkNotificationTask:
    def test_sends_the_mail(self, owner):
        send_telegram_link_notification(owner.pk, CONNECTED)
        assert len(mail.outbox) == 1

    def test_a_deleted_user_is_dropped_without_retrying(self, db):
        send_telegram_link_notification(0, CONNECTED)
        assert mail.outbox == []

    def test_a_send_failure_is_retried(self, owner):
        with (
            patch(
                "apps.users.notifications.send_telegram_link_email",
                side_effect=Exception("smtp is down"),
            ),
            patch.object(
                send_telegram_link_notification,
                "retry",
                return_value=RuntimeError("retrying"),
            ) as retry,
            pytest.raises(RuntimeError, match="retrying"),
        ):
            send_telegram_link_notification(owner.pk, CONNECTED)
        retry.assert_called_once()
