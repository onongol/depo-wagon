from rest_framework.permissions import BasePermission

from apps.core.constants import EmployeeRole


class HasEmployeeRole(BasePermission):
    allowed_roles = []

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            return request.user.employee.role in self.allowed_roles
        except Exception:
            return False


class IsInspector(HasEmployeeRole):
    allowed_roles = [EmployeeRole.INSPECTOR]


class IsEngineer(HasEmployeeRole):
    allowed_roles = [EmployeeRole.ENGINEER]


class IsMaster(HasEmployeeRole):
    allowed_roles = [EmployeeRole.MASTER]


class IsManager(HasEmployeeRole):
    allowed_roles = [EmployeeRole.MANAGER]


class IsInspectorOrEngineer(HasEmployeeRole):
    allowed_roles = [EmployeeRole.INSPECTOR, EmployeeRole.ENGINEER]


class IsEngineerOrManager(HasEmployeeRole):
    allowed_roles = [EmployeeRole.ENGINEER, EmployeeRole.MANAGER]


class IsAnyEmployee(HasEmployeeRole):
    allowed_roles = list(EmployeeRole.values)
