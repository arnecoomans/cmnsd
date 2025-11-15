from django import template

register = template.Library()

def to_float(value):
    """Safely convert to float, return 0 on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

@register.filter
def div(value, arg):
    """Divide value by arg."""
    v = to_float(value)
    a = to_float(arg)
    if a == 0:
        return 0
    return v / a

@register.filter
def mul(value, arg):
    """Multiply value by arg."""
    return to_float(value) * to_float(arg)

@register.filter
def sub(value, arg):
    """Subtract arg from value."""
    return to_float(value) - to_float(arg)

@register.filter
def addf(value, arg):
    """Add arg to value (float-based add)."""
    return to_float(value) + to_float(arg)

@register.filter
def floatfmt(value, decimals=2):
    """Format a float with N decimals."""
    try:
        decimals = int(decimals)
    except:
        decimals = 2
    return f"{to_float(value):.{decimals}f}"

@register.filter
def floatdot(value):
    """Convert a float to dot-decimal string."""
    try:
        return str(value).replace(',', '.')
    except:
        return value