from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render
from django.utils import timezone

from apps.core.constants import WagonStatus, WagonType
from apps.core.models import Wagon
from apps.web.constants import PAGE_SIZE
from apps.web.decorators import employee_required

WAGON_SORTABLE_FIELDS = {
    "number",
    "wagon_type",
    "status",
    "manufacture_year",
    "next_repair_date",
    "mileage_km",
    "open_defects",
}


@employee_required
def wagon_list(request):
    today = timezone.now().date()
    qs = Wagon.objects.annotate(
        open_defects=Count("defects", filter=Q(defects__status="open"))
    )

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(number__icontains=q)

    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    wagon_type = request.GET.get("wagon_type", "")
    if wagon_type:
        qs = qs.filter(wagon_type=wagon_type)

    order_by = request.GET.get("order_by", "number")
    direction = request.GET.get("direction", "asc")
    if order_by not in WAGON_SORTABLE_FIELDS:
        order_by, direction = "number", "asc"
    qs = qs.order_by(f"-{order_by}" if direction == "desc" else order_by)

    paginator = Paginator(qs, PAGE_SIZE)
    wagons = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "wagons": wagons,
        "today": today,
        "q": q,
        "selected_status": status,
        "selected_wagon_type": wagon_type,
        "status_choices": WagonStatus.choices,
        "type_choices": WagonType.choices,
        "total_count": paginator.count,
        "filter_qs": params.urlencode(),
        "has_active_filters": bool(q or status or wagon_type),
    }

    if request.headers.get("HX-Request"):
        return render(request, "web/wagons/table/wagons_table.html", context)

    return render(request, "web/wagons/list.html", context)
