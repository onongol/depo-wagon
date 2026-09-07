from typing import NamedTuple

from django_components import Component, register


@register("filter_buttons")
class FilterButtons(Component):
    template_name = "filter_buttons/filter_buttons.html"

    class Kwargs(NamedTuple):
        target: str
        has_active_filters: bool = False
        clear_url: str = ""

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "clear_id": kwargs.target.lstrip("#") + "-clear",
            "has_active_filters": kwargs.has_active_filters,
            "clear_url": kwargs.clear_url,
        }
