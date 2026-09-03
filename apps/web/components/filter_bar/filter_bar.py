from django_components import Component, register


@register("filter_bar")
class FilterBar(Component):
    template_name = "filter_bar/filter_bar.html"

    def get_context_data(
        self,
        url: str,
        target: str,
        *,
        has_active_filters: bool = False,
        clear_url: str = "",
        **kwargs,
    ):
        return {
            "url": url,
            "target": target,
            "has_active_filters": has_active_filters,
            "clear_url": clear_url,
        }
