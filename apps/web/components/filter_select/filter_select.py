from django_components import Component, register


@register("filter_select")
class FilterSelect(Component):
    template_name = "filter_select/filter_select.html"

    def get_context_data(  # noqa: PLR0913 — the signature is the component's template contract
        self,
        name: str,
        choices,
        *,
        selected: str = "",
        placeholder: str = "",
        url: str = "",
        target: str = "",
        **kwargs,
    ):
        return {
            "name": name,
            "choices": choices,
            "selected": selected,
            "placeholder": placeholder,
            "url": url,
            "target": target,
        }
