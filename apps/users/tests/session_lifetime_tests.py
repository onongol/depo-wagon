from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from apps.core.constants import EmployeeRole

User = get_user_model()


@pytest.fixture
def employee_user(db):
    user = User.objects.create_user(email="session@depot.mn", password="pass123")
    baker.make("core.Employee", user=user, role=EmployeeRole.INSPECTOR)
    return user


@pytest.mark.django_db
def test_activity_pushes_the_session_expiry_forward(client, employee_user):
    """SESSION_COOKIE_AGE is an idle timeout, not a cap on how long a shift lasts.

    That only holds because of SESSION_SAVE_EVERY_REQUEST; dropping it as a
    write-saving measure would silently turn the eight hours into a hard limit.
    """
    client.force_login(employee_user)
    client.get(reverse("web:wagon_list"))

    key = client.session.session_key
    Session.objects.filter(session_key=key).update(
        expire_date=timezone.now() + timedelta(minutes=1)
    )

    client.get(reverse("web:wagon_list"))

    expires_in = Session.objects.get(session_key=key).expire_date - timezone.now()
    assert expires_in > timedelta(hours=7)
