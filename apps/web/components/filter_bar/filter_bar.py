from typing import NamedTuple

from django_components import Component, register


@register("filter_bar")
class FilterBar(Component):
    template_name = "filter_bar/filter_bar.html"

    class Kwargs(NamedTuple):
        url: str
        target: str
        has_active_filters: bool = False
        clear_url: str = ""

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "url": kwargs.url,
            "target": kwargs.target,
            "has_active_filters": kwargs.has_active_filters,
            "clear_url": kwargs.clear_url,
        }
