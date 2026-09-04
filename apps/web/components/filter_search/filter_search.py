from typing import NamedTuple

from django_components import Component, register


@register("filter_search")
class FilterSearch(Component):
    template_name = "filter_search/filter_search.html"

    class Kwargs(NamedTuple):
        url: str
        target: str
        name: str = "q"
        value: str = ""
        placeholder: str = ""

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "url": kwargs.url,
            "target": kwargs.target,
            "name": kwargs.name,
            "value": kwargs.value,
            "placeholder": kwargs.placeholder,
        }
