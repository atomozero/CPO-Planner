from django import template

register = template.Library()

@register.filter
def getattr(obj, attr_name):
    """Returns the named attribute from an object"""
    try:
        return getattr(obj, attr_name)
    except AttributeError:
        return None

@register.filter
def as_crispy_field(field):
    """Returns the field rendered as a crispy field"""
    return field

@register.filter
def add(value, arg):
    """Adds the arg to the value."""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return value + arg
        except Exception:
            return ''
        
@register.filter
def sub(value, arg):
    """Subtracts the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return ''
        
@register.filter
def mul(value, arg):
    """Multiplies the value by the arg."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
        
@register.filter
def div(value, arg):
    """Divides the value by the arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''