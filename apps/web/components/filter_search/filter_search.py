from django_components import Component, register


@register("filter_search")
class FilterSearch(Component):
    template_name = "filter_search/filter_search.html"

    def get_context_data(
        self,
        url: str,
        target: str,
        name: str = "q",
        value: str = "",
        placeholder: str = "",
        **kwargs,
    ):
        return {
            "url": url,
            "target": target,
            "name": name,
            "value": value,
            "placeholder": placeholder,
        }
