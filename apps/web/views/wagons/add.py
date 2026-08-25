from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from apps.web.forms import WagonForm


@login_required
def wagon_add(request):
    form = WagonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, _("Wagon added successfully."))
        return redirect("web:wagon_list")
    return render(request, "web/wagons/add.html", {"form": form})
