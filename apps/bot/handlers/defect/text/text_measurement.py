from typing import TYPE_CHECKING

from aiogram.utils.formatting import Bold, Italic, Text, as_list, as_marked_section
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from apps.bot.user_data import MeasurementEntry

_EXAMPLE = _("(e.g. 12.5)")


def _measurement_line(measurement: MeasurementEntry) -> Text:
    line = Text(measurement.dimension_label, ": ", Bold(measurement.value))
    if measurement.unit:
        line = Text(line, " ", measurement.unit)
    return line


def build_measurements_text(measurements: list[MeasurementEntry]) -> Text:
    if not measurements:
        return Text("📐 ", _("Choose a dimension to add a measurement, or skip:"))

    return as_list(
        as_marked_section(
            Text("📐 ", Bold(_("Measurements"), ":")),
            *(_measurement_line(m) for m in measurements),
            marker="🔹 ",
        ),
        _("Choose a dimension to add another, or press Done:"),
        sep="\n\n",
    )


def build_ask_value_text(label: str, unit: str) -> Text:
    return as_list(
        Text("📏 ", Bold(f"{label}, {unit}" if unit else label)),
        Text(_("Enter the value"), " ", Italic(_EXAMPLE), ":"),
        sep="\n\n",
    )


def build_value_invalid_text() -> Text:
    return Text("❌ ", _("Please enter a number"), " ", Italic(_EXAMPLE), ":")
