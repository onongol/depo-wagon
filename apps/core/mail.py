import base64
import logging
from email.mime.base import MIMEBase

from django.conf import settings
from django.core.mail import get_connection
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMultiAlternatives
from kombu.exceptions import OperationalError

logger = logging.getLogger(__name__)


def _serialize_attachment(attachment) -> list:
    if isinstance(attachment, MIMEBase):
        raise TypeError("a MIMEBase attachment cannot be queued")
    filename, content, mimetype = attachment
    binary = isinstance(content, bytes)
    if binary:
        content = base64.b64encode(content).decode("ascii")
    return [filename, content, mimetype, binary]


def _deserialize_attachment(attachment) -> tuple:
    filename, content, mimetype, binary = attachment
    return filename, base64.b64decode(content) if binary else content, mimetype


def serialize_message(message) -> dict:
    return {
        "subject": message.subject,
        "body": message.body,
        "from_email": message.from_email,
        "to": list(message.to),
        "cc": list(message.cc),
        "bcc": list(message.bcc),
        "reply_to": list(message.reply_to),
        "headers": dict(message.extra_headers),
        "content_subtype": message.content_subtype,
        "alternatives": [
            [content, mimetype]
            for content, mimetype in getattr(message, "alternatives", [])
        ],
        "attachments": [_serialize_attachment(a) for a in message.attachments],
    }


def deserialize_message(data: dict) -> EmailMultiAlternatives:
    message = EmailMultiAlternatives(
        subject=data["subject"],
        body=data["body"],
        from_email=data["from_email"],
        to=data["to"],
        cc=data["cc"],
        bcc=data["bcc"],
        reply_to=data["reply_to"],
        headers=data["headers"],
        alternatives=[tuple(a) for a in data["alternatives"]],
    )
    message.content_subtype = data["content_subtype"]
    for attachment in data["attachments"]:
        message.attach(*_deserialize_attachment(attachment))
    return message


def deliver(email_messages, fail_silently: bool = False) -> int:
    connection = get_connection(
        backend=settings.EMAIL_DELIVERY_BACKEND, fail_silently=fail_silently
    )
    return connection.send_messages(email_messages) or 0


class CeleryEmailBackend(BaseEmailBackend):
    """Hands rendered messages to Celery so a slow relay cannot hold a request."""

    def send_messages(self, email_messages) -> int:
        from apps.core.tasks import send_queued_email

        queued = 0
        for message in email_messages:
            try:
                payload = serialize_message(message)
            except TypeError:
                logger.warning(
                    "Message to %s is not queueable, sending it inline", message.to
                )
                queued += deliver([message], self.fail_silently)
                continue

            try:
                send_queued_email.delay(payload)
            except OperationalError:
                logger.exception(
                    "Could not queue mail to %s, sending it inline", message.to
                )
                queued += deliver([message], self.fail_silently)
            else:
                queued += 1
        return queued
