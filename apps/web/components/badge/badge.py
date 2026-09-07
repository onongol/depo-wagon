from typing import TYPE_CHECKING, NamedTuple

from django_components import Component, register

if TYPE_CHECKING:
    from apps.core.models import Wagon

_COLORS = {
    "emerald": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
    "green": "bg-green-100 text-green-700 dark:bg-green-500/20 dark:text-green-400",
    "red": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
    "orange": "bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400",
    "yellow": "bg-yellow-100 text-yellow-700 dark:bg-yellow-500/20 dark:text-yellow-400",
    "blue": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
    "purple": "bg-purple-100 text-purple-700 dark:bg-purple-500/20 dark:text-purple-400",
    "indigo": "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-400",
    "rose": "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-400",
    "gray": "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400",
}


_WAGON_STATUS_COLORS = {
    "active": "emerald",
    "ready": "green",
    "repair": "orange",
    "waiting": "yellow",
    "inspection": "purple",
    "arrived": "blue",
}


@register("badge")
class Badge(Component):
    template_name = "badge/badge.html"

    class Kwargs(NamedTuple):
        label: str
        color: str = "gray"

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "label": kwargs.label,
            "classes": _COLORS.get(kwargs.color, _COLORS["gray"]),
        }


@register("wagon_status_badge")
class WagonStatusBadge(Component):
    template_name = "badge/badge.html"

    class Kwargs(NamedTuple):
        wagon: Wagon

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        color = _WAGON_STATUS_COLORS.get(kwargs.wagon.status, "gray")
        return {
            "label": kwargs.wagon.get_status_display(),
            "classes": _COLORS[color],
        }
