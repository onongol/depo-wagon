from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render

from apps.ai_service.constants import DocumentStatus
from apps.ai_service.models import DepotDocument
from apps.web.constants import PAGE_SIZE
from apps.web.decorators import employee_required


@employee_required
def document_list(request):
    qs = DepotDocument.objects.annotate(chunks_count=Count("chunks")).order_by(
        "-created_at"
    )

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(title__icontains=q)

    status = request.GET.get("status", "")
    if status:
        qs = qs.filter(status=status)

    paginator = Paginator(qs, PAGE_SIZE)
    documents = paginator.get_page(request.GET.get("page", 1))

    params = request.GET.copy()
    params.pop("page", None)

    return render(
        request,
        "web/documents/list.html",
        {
            "documents": documents,
            "q": q,
            "selected_status": status,
            "status_choices": DocumentStatus.choices,
            "total_count": paginator.count,
            "filter_qs": params.urlencode(),
        },
    )
