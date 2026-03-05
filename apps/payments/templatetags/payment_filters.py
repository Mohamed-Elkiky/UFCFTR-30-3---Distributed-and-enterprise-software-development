from django import template

register = template.Library()


@register.filter
def pence_to_pounds(value):
    """Convert integer pence value to a pounds string with 2 decimal places."""
    try:
        return f"{int(value) / 100:.2f}"
    except (TypeError, ValueError):
        return "0.00"
