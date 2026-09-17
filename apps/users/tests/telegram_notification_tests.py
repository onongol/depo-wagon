from unittest.mock import patch

import pytest
from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from kombu.exceptions import OperationalError

from apps.core.tasks import send_queued_email
from apps.users.notifications import (
    CONNECTED,
    DISCONNECTED,
    build_telegram_link_email,
    notify_telegram_link_change,
)

User = get_user_model()

QUEUE = "apps.core.tasks.send_queued_email.apply_async"


@pytest.fixture
def owner(db):
    user = User.objects.create_user(email="owner@depot.mn", password="pass12345")
    EmailAddress.objects.create(
        user=user, email=user.email, verified=True, primary=True
    )
    return user


@pytest.mark.django_db
class TestBuildTelegramLinkEmail:
    @pytest.mark.parametrize("action", [CONNECTED, DISCONNECTED])
    def test_goes_to_the_primary_address(self, owner, action):
        assert build_telegram_link_email(owner, action).to == ["owner@depot.mn"]

    def test_subject_carries_the_project_prefix(self, owner, settings):
        settings.ACCOUNT_EMAIL_SUBJECT_PREFIX = "[Depo Wagon] "
        message = build_telegram_link_email(owner, CONNECTED)
        assert message.subject.startswith("[Depo Wagon] ")

    def test_the_two_actions_read_differently(self, owner):
        connected = build_telegram_link_email(owner, CONNECTED)
        disconnected = build_telegram_link_email(owner, DISCONNECTED)
        assert connected.subject != disconnected.subject
        assert connected.body != disconnected.body

    def test_body_links_to_the_telegram_page(self, owner, settings):
        settings.SITE_URL = "https://depowagon.mn/"
        message = build_telegram_link_email(owner, CONNECTED)
        assert "https://depowagon.mn/telegram/" in message.body

    def test_falls_back_to_the_account_email_when_unconfirmed(self, db):
        user = User.objects.create_user(email="new@depot.mn", password="pass12345")
        assert build_telegram_link_email(user, CONNECTED).to == ["new@depot.mn"]

    def test_a_user_with_no_address_at_all_gets_nothing(self, db):
        user = User.objects.create_user(email="none@depot.mn", password="pass12345")
        user.email = ""
        assert build_telegram_link_email(user, CONNECTED) is None


@pytest.mark.django_db
class TestNotifyTelegramLinkChange:
    def test_the_notice_reaches_the_owner_only_through_the_queue(self, owner):
        with patch(QUEUE) as queue:
            notify_telegram_link_change(owner, CONNECTED)
        assert mail.outbox == []

        send_queued_email(*queue.call_args.args[0])
        assert mail.outbox[0].to == ["owner@depot.mn"]

    def test_publishes_once_without_retrying(self, owner):
        with patch(QUEUE) as queue:
            notify_telegram_link_change(owner, CONNECTED)
        queue.assert_called_once()
        assert queue.call_args.kwargs == {"retry": False}

    def test_the_switch_skips_all_the_work(self, owner, settings):
        settings.ACCOUNT_EMAIL_NOTIFICATIONS = False
        with (
            patch(QUEUE) as queue,
            patch("apps.users.notifications.build_telegram_link_email") as build,
        ):
            notify_telegram_link_change(owner, CONNECTED)
        build.assert_not_called()
        queue.assert_not_called()

    def test_an_owner_without_an_address_queues_nothing(self, db):
        user = User.objects.create_user(email="none@depot.mn", password="pass12345")
        user.email = ""
        with patch(QUEUE) as queue:
            notify_telegram_link_change(user, CONNECTED)
        queue.assert_not_called()

    def test_a_dead_broker_is_logged_not_raised(self, owner):
        with (
            patch(QUEUE, side_effect=OperationalError("broker is down")),
            patch("apps.users.notifications.logger") as logger,
        ):
            notify_telegram_link_change(owner, CONNECTED)
        logger.exception.assert_called_once()
