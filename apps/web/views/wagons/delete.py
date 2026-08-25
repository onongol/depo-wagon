from django.contrib import messages
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _

from apps.core.models import Wagon
from apps.web.decorators import engineer_or_manager_required


@engineer_or_manager_required
def wagon_delete_bulk(request):
    if request.method == "POST":
        ids = request.POST.getlist("ids")
        deleted, _details = Wagon.objects.filter(pk__in=ids).delete()
        messages.success(request, _("Deleted %(count)d wagon(s).") % {"count": deleted})
    return redirect("web:wagon_list")
