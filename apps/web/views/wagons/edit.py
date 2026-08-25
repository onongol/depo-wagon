from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.core.models import Wagon
from apps.web.decorators import engineer_or_manager_required
from apps.web.forms import WagonForm


@engineer_or_manager_required
def wagon_edit(request, pk):
    wagon = get_object_or_404(Wagon, pk=pk)
    form = WagonForm(request.POST or None, instance=wagon)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Wagon updated successfully."))
        return redirect("web:wagon_list")
    return render(request, "web/wagons/edit.html", {"form": form, "wagon": wagon})
