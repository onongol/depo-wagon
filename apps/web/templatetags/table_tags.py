from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def sort_url(context, field):
    request = context["request"]
    params = request.GET.copy()
    current_order = params.get("order_by", "")
    current_dir = params.get("direction", "asc")
    params["order_by"] = field
    params["direction"] = (
        "desc" if current_order == field and current_dir == "asc" else "asc"
    )
    params.pop("page", None)
    return "?" + params.urlencode()
