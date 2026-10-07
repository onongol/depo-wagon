from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Code, Italic, Text, as_list
from django.utils.translation import gettext_lazy as _

from apps.bot.utils.defect_fields import measurement_line

if TYPE_CHECKING:
    from apps.bot.user_data import MeasurementEntry

_EXAMPLE = _("(e.g. 12.5)")


def build_measurement_line(measurement: MeasurementEntry) -> Text:
    return measurement_line(
        measurement.dimension_label, measurement.value, measurement.unit
    )


def build_ask_measurement_text(*, any_saved: bool) -> Text:
    if any_saved:
        return Text("📐 ", _("Choose a dimension to add another, or press Done:"))
    return Text("📐 ", _("Choose a dimension to add a measurement, or skip:"))


def build_ask_value_text(label: str, unit: str) -> Text:
    return as_list(
        Text("📏 ", Bold(f"{label}, {unit}" if unit else label)),
        Text(_("Enter the value"), " ", Italic(_EXAMPLE), ":"),
        sep="\n\n",
    )


def build_value_invalid_text(typed: str) -> Text:
    return Text("❌ ", _("Not a number:"), " ", Code(typed))
