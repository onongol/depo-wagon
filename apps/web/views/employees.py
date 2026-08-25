from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from apps.core.constants import Department, EmployeeRole
from apps.core.models import Employee
from apps.web.constants import PAGE_SIZE
from apps.web.decorators import employee_required


@employee_required
def employee_list(request):
    qs = Employee.objects.annotate(
        inspections_count=Count("inspected_defects", distinct=True)
    ).order_by("employee_id")

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(employee_id__icontains=q)
        )

    role = request.GET.get("role", "")
    if role:
        qs = qs.filter(role=role)

    department = request.GET.get("department", "")
    if department:
        qs = qs.filter(department=department)

    is_active = request.GET.get("is_active", "")
    if is_active == "1":
        qs = qs.filter(is_active=True)
    elif is_active == "0":
        qs = qs.filter(is_active=False)

    paginator = Paginator(qs, PAGE_SIZE)
    employees = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "web/employees/list.html",
        {
            "employees": employees,
            "q": q,
            "selected_role": role,
            "selected_department": department,
            "selected_is_active": is_active,
            "role_choices": EmployeeRole.choices,
            "department_choices": Department.choices,
            "total_count": paginator.count,
            "filter_qs": params.urlencode(),
        },
    )
