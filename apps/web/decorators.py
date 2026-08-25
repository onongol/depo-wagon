from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from apps.core.constants import EmployeeRole


def role_required(*roles):
    """Restrict a view to employees holding one of ``roles``.

    Superusers always pass. This is the view-level counterpart of
    apps.users.permissions.HasEmployeeRole, which guards the same models on
    the REST API — keep the two in sync.
    """
    allowed = set(roles)

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            employee = getattr(request.user, "employee", None)
            if request.user.is_superuser or (
                employee is not None and employee.role in allowed
            ):
                return view(request, *args, **kwargs)
            raise PermissionDenied

        return login_required(wrapper)

    return decorator


employee_required = role_required(*EmployeeRole.values)
engineer_or_manager_required = role_required(
    EmployeeRole.ENGINEER, EmployeeRole.MANAGER
)
