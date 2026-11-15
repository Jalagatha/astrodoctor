from django import template

register = template.Library()


@register.filter
def signed(value, digits=1):
    """Format a number with an explicit sign: 0.42 -> '+0.4'."""
    if value is None or value == "":
        return "–"
    try:
        return f"{float(value):+.{int(digits)}f}"
    except (TypeError, ValueError):
        return value
