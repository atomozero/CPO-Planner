from django import template

register = template.Library()

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
        
@register.filter
def get_item(dictionary, key):
    """Gets an item from a dictionary."""
    if dictionary is None:
        return None
    return dictionary.get(key)