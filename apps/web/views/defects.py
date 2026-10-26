from django.core.paginator import Paginator
from django.shortcuts import render

from apps.defects.constants import DefectSeverity, DefectStatus, DefectType
from apps.defects.models import Defect
from apps.web.constants import PAGE_SIZE
from apps.web.decorators import employee_required


@employee_required
def defect_list(request):
    qs = (
        Defect.objects.visible_to(request.user)
        .select_related("wagon", "inspector")
        .order_by("-inspected_at")
    )

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(wagon__number__icontains=q)

    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    severity = request.GET.get("severity", "")
    if severity:
        qs = qs.filter(severity=severity)

    defect_type = request.GET.get("defect_type", "")
    if defect_type:
        qs = qs.filter(defect_type=defect_type)

    paginator = Paginator(qs, PAGE_SIZE)
    defects = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "web/defects/list.html",
        {
            "defects": defects,
            "q": q,
            "selected_status": status,
            "selected_severity": severity,
            "selected_defect_type": defect_type,
            "status_choices": DefectStatus.choices,
            "severity_choices": DefectSeverity.choices,
            "type_choices": DefectType.choices,
            "total_count": paginator.count,
            "filter_qs": params.urlencode(),
        },
    )
