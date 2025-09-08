from django import template


register = template.Library()


@register.filter
def div(a, b):
    try:
        a_val = float(a)
        b_val = float(b)
        if b_val == 0:
            return 0
        return a_val / b_val
    except (TypeError, ValueError):
        return 0


@register.filter
def mul(a, b):
    try:
        return float(a) * float(b)
    except (TypeError, ValueError):
        return 0




