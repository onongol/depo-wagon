from types import SimpleNamespace

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import DatabaseError
from model_bakery import baker

from apps.core.constants import EmployeeRole
from apps.users.permissions import IsAnyEmployee, IsEngineerOrManager, IsInspector

User = get_user_model()


def _request(user):
    return SimpleNamespace(user=user)


def _user_with_role(role, email="perm@depot.mn"):
    user = User.objects.create_user(email=email, password="pass123")
    baker.make("core.Employee", user=user, role=role)
    return user


@pytest.mark.django_db
class TestHasEmployeeRole:
    def test_a_missing_user_is_denied(self):
        assert not IsInspector().has_permission(_request(None), None)

    def test_an_anonymous_user_is_denied(self):
        assert not IsInspector().has_permission(_request(AnonymousUser()), None)

    def test_a_superuser_passes_without_an_employee(self):
        user = User.objects.create_superuser(email="admin@depot.mn", password="pass123")
        assert IsInspector().has_permission(_request(user), None)

    def test_the_matching_role_passes(self):
        user = _user_with_role(EmployeeRole.INSPECTOR)
        assert IsInspector().has_permission(_request(user), None)

    def test_another_role_is_denied(self):
        user = _user_with_role(EmployeeRole.MASTER)
        assert not IsInspector().has_permission(_request(user), None)

    def test_an_authenticated_user_without_an_employee_is_denied(self):
        user = User.objects.create_user(email="orphan@depot.mn", password="pass123")
        assert not IsAnyEmployee().has_permission(_request(user), None)

    def test_either_of_two_allowed_roles_passes(self):
        engineer = _user_with_role(EmployeeRole.ENGINEER, "eng@depot.mn")
        manager = _user_with_role(EmployeeRole.MANAGER, "mgr@depot.mn")
        assert IsEngineerOrManager().has_permission(_request(engineer), None)
        assert IsEngineerOrManager().has_permission(_request(manager), None)


class _UserWithUnreachableEmployee:
    is_authenticated = True
    is_superuser = False

    @property
    def employee(self):
        msg = "connection lost"
        raise DatabaseError(msg)


class TestAnUnreachableDatabaseIsNotADenial:
    """An outage must not be reported as "permission denied"."""

    def test_a_database_error_propagates(self):
        request = _request(_UserWithUnreachableEmployee())
        with pytest.raises(DatabaseError):
            IsInspector().has_permission(request, None)
