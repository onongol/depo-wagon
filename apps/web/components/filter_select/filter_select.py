from typing import NamedTuple

from django_components import Component, register


@register("filter_select")
class FilterSelect(Component):
    template_name = "filter_select/filter_select.html"

    class Kwargs(NamedTuple):
        name: str
        choices: list[tuple[str, str]]
        selected: str = ""
        placeholder: str = ""
        url: str = ""
        target: str = ""

    def get_template_data(self, args, kwargs: Kwargs, slots, context):
        return {
            "name": kwargs.name,
            "choices": kwargs.choices,
            "selected": kwargs.selected,
            "placeholder": kwargs.placeholder,
            "url": kwargs.url,
            "target": kwargs.target,
        }
