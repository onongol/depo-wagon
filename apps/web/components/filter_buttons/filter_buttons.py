from django_components import Component, register


@register("filter_buttons")
class FilterButtons(Component):
    template_name = "filter_buttons/filter_buttons.html"

    def get_context_data(
        self,
        target: str,
        has_active_filters: bool = False,
        clear_url: str = "",
        **kwargs,
    ):
        return {
            "clear_id": target.lstrip("#") + "-clear",
            "has_active_filters": has_active_filters,
            "clear_url": clear_url,
        }
