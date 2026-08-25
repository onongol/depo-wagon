from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.models import Wagon


class WagonForm(forms.ModelForm):
    class Meta:
        model = Wagon
        fields = [
            "number",
            "wagon_type",
            "manufacture_year",
            "status",
            "repair_type",
            "last_repair_date",
            "next_repair_date",
            "mileage_km",
            "owner",
            "notes",
        ]
        widgets = {
            "last_repair_date": forms.DateInput(attrs={"type": "date"}),
            "next_repair_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "number": _("Wagon Number"),
            "wagon_type": _("Type"),
            "manufacture_year": _("Manufacture Year"),
            "status": _("Status"),
            "repair_type": _("Repair Type"),
            "last_repair_date": _("Last Repair Date"),
            "next_repair_date": _("Next Repair Date"),
            "mileage_km": _("Mileage (km)"),
            "owner": _("Owner"),
            "notes": _("Notes"),
        }
