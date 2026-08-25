from django.shortcuts import render
from django.utils import timezone

from apps.core.models import Employee, Wagon
from apps.defects.models import Defect
from apps.web.decorators import employee_required


@employee_required
def dashboard(request):
    today = timezone.now().date()
    stats = {
        "total_wagons": Wagon.objects.count(),
        "open_defects": Defect.objects.filter(status="open").count(),
        "repair_due": Wagon.objects.filter(next_repair_date__lte=today).count(),
        "total_employees": Employee.objects.filter(is_active=True).count(),
    }
    return render(request, "web/dashboard.html", {"stats": stats})
