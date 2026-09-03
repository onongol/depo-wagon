from email.mime.base import MIMEBase
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.mail import EmailMultiAlternatives, get_connection
from kombu.exceptions import OperationalError

from apps.core.mail import deserialize_message, serialize_message
from apps.core.tasks import send_queued_email

CELERY_BACKEND = "apps.core.mail.CeleryEmailBackend"


def make_message():
    message = EmailMultiAlternatives(
        "Confirm your address",
        "Plain body",
        "noreply@depot.mn",
        ["owner@depot.mn"],
        cc=["cc@depot.mn"],
        bcc=["bcc@depot.mn"],
        reply_to=["support@depot.mn"],
        headers={"X-Depo": "wagon"},
    )
    message.attach_alternative("<p>HTML body</p>", "text/html")
    return message


class TestRoundTrip:
    @pytest.mark.parametrize(
        "field", ["subject", "body", "from_email", "to", "cc", "bcc", "reply_to"]
    )
    def test_addressing_survives(self, field):
        original = make_message()
        restored = deserialize_message(serialize_message(original))
        assert getattr(restored, field) == getattr(original, field)

    def test_extra_headers_survive(self):
        restored = deserialize_message(serialize_message(make_message()))
        assert restored.extra_headers == {"X-Depo": "wagon"}

    def test_the_html_alternative_survives(self):
        restored = deserialize_message(serialize_message(make_message()))
        assert tuple(restored.alternatives[0]) == ("<p>HTML body</p>", "text/html")

    def test_a_binary_attachment_survives(self):
        original = make_message()
        original.attach("report.pdf", b"\x00\x01\x02not-text", "application/pdf")
        restored = deserialize_message(serialize_message(original))
        assert tuple(restored.attachments[0]) == (
            "report.pdf",
            b"\x00\x01\x02not-text",
            "application/pdf",
        )

    def test_a_text_attachment_stays_text(self):
        original = make_message()
        original.attach("notes.txt", "just text", "text/plain")
        restored = deserialize_message(serialize_message(original))
        assert restored.attachments[0][1] == "just text"

    def test_an_html_only_message_keeps_its_content_type(self):
        original = mail.EmailMessage(
            "Subject", "<p>body</p>", "a@depot.mn", ["b@depot.mn"]
        )
        original.content_subtype = "html"
        assert (
            deserialize_message(serialize_message(original)).content_subtype == "html"
        )


class TestQueueing:
    def test_each_message_becomes_one_task(self):
        with patch("apps.core.tasks.send_queued_email.delay") as delay:
            sent = get_connection(backend=CELERY_BACKEND).send_messages(
                [make_message(), make_message()]
            )
        assert sent == 2
        assert delay.call_count == 2
        assert mail.outbox == []

    def test_the_queued_payload_is_json_safe(self):
        import json

        with patch("apps.core.tasks.send_queued_email.delay") as delay:
            get_connection(backend=CELERY_BACKEND).send_messages([make_message()])
        json.dumps(delay.call_args.args[0])

    def test_nothing_to_send_queues_nothing(self):
        with patch("apps.core.tasks.send_queued_email.delay") as delay:
            assert get_connection(backend=CELERY_BACKEND).send_messages([]) == 0
        delay.assert_not_called()


class TestFallbackToInlineDelivery:
    def test_a_dead_broker_still_delivers(self):
        with patch(
            "apps.core.tasks.send_queued_email.delay",
            side_effect=OperationalError("broker is down"),
        ):
            sent = get_connection(backend=CELERY_BACKEND).send_messages(
                [make_message()]
            )
        assert sent == 1
        assert mail.outbox[0].to == ["owner@depot.mn"]

    def test_an_unserializable_attachment_still_delivers(self):
        message = make_message()
        part = MIMEBase("application", "octet-stream")
        part.set_payload(b"raw")
        message.attach(part)

        with patch("apps.core.tasks.send_queued_email.delay") as delay:
            sent = get_connection(backend=CELERY_BACKEND).send_messages([message])
        assert sent == 1
        delay.assert_not_called()
        assert mail.outbox[0].to == ["owner@depot.mn"]


class TestSendQueuedEmailTask:
    def test_the_worker_delivers_the_payload(self):
        send_queued_email(serialize_message(make_message()))
        assert mail.outbox[0].subject == "Confirm your address"
        assert tuple(mail.outbox[0].alternatives[0]) == (
            "<p>HTML body</p>",
            "text/html",
        )

    def test_a_delivery_failure_is_retried(self):
        with (
            patch("apps.core.mail.deliver", side_effect=Exception("smtp is down")),
            patch.object(
                send_queued_email, "retry", return_value=RuntimeError("retrying")
            ) as retry,
            pytest.raises(RuntimeError, match="retrying"),
        ):
            send_queued_email(serialize_message(make_message()))
        retry.assert_called_once()
