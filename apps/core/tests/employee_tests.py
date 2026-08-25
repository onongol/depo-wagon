import pytest
from django.contrib.auth import get_user_model

from apps.core.constants import Department, EmployeeRole
from apps.core.models import Employee

User = get_user_model()


def make_employee(**kwargs):
    defaults = {
        "employee_id": "1234",
        "first_name": "Бат",
        "last_name": "Болд",
        "role": EmployeeRole.INSPECTOR,
    }
    defaults.update(kwargs)
    return Employee(**defaults)


@pytest.mark.django_db
class TestEmployeeModel:
    def test_str(self):
        emp = make_employee()
        assert "1234" in str(emp)
        assert "" in str(emp)

    def test_full_name(self):
        emp = make_employee(first_name="Elbegdorj", last_name="Tsakhiagiin")
        assert emp.full_name == "Tsakhiagiin Elbegdorj"

    def test_short_name_with_both_names(self):
        emp = make_employee(first_name="Elbegdorj", last_name="Tsakhiagiin")
        assert emp.short_name == "T.Elbegdorj"

    def test_short_name_only_first_name(self):
        emp = make_employee(first_name="Elbegdorj", last_name="")
        assert emp.short_name == "Elbegdorj"

    def test_short_name_only_last_name(self):
        emp = make_employee(first_name="", last_name="Tsakhiagiin")
        assert emp.short_name == "Tsakhiagiin"

    def test_short_name_fallback_to_employee_id(self):
        emp = make_employee(first_name="", last_name="")
        assert emp.short_name == "1234"

    def test_is_active_by_default(self):
        emp = make_employee()
        assert emp.is_active is True

    def test_employee_id_is_unique(self):
        make_employee(employee_id="12349").save()
        with pytest.raises(Exception):
            make_employee(employee_id="12349").save()


@pytest.mark.django_db
class TestEmployeeSave:
    def test_empty_phone_saved_as_null(self):
        emp = make_employee(phone="")
        emp.save()
        emp.refresh_from_db()
        assert emp.phone is None

    def test_empty_email_saved_as_null(self):
        emp = make_employee(email="")
        emp.save()
        emp.refresh_from_db()
        assert emp.email is None

    def test_phone_unique_null_allows_multiple(self):
        make_employee(employee_id="12345", phone="").save()
        make_employee(employee_id="12346", phone="").save()  # Should not raise an error

    def test_phone_is_unique(self):
        make_employee(employee_id="12350", phone="+97699001122").save()
        with pytest.raises(Exception):
            make_employee(employee_id="12351", phone="+97699001122").save()

    def test_email_is_unique(self):
        make_employee(employee_id="12352", email="test@depot.mn").save()
        with pytest.raises(Exception):
            make_employee(employee_id="12353", email="test@depot.mn").save()

    def test_telegram_id_is_unique(self):
        make_employee(employee_id="12354", telegram_id=123456789).save()
        with pytest.raises(Exception):
            make_employee(employee_id="12355", telegram_id=123456789).save()

    def test_deactivate_employee_deactivates_user(self):
        user = User.objects.create_user(email="emp@example.com", password="pass123")
        emp = make_employee(employee_id="12347", user=user, is_active=True)
        emp.save()

        emp.is_active = False
        emp.save()

        user.refresh_from_db()
        assert user.is_active is False

    def test_activate_employee_activates_user(self):
        user = User.objects.create_user(
            email="emp2@example.com", password="pass123", is_active=False
        )
        emp = make_employee(employee_id="12348", user=user, is_active=False)
        emp.save()

        emp.is_active = True
        emp.save()

        user.refresh_from_db()
        assert user.is_active is True


@pytest.mark.django_db
class TestEmployeeDepartment:
    def test_department_blank_by_default(self):
        emp = make_employee()
        assert emp.department == ""

    def test_department_can_be_set(self):
        emp = make_employee(department=Department.BOGIE)
        emp.save()
        emp.refresh_from_db()
        assert emp.department == Department.BOGIE

    def test_department_is_optional(self):
        emp = make_employee()
        emp.save()
        emp.refresh_from_db()
        assert emp.department == ""
