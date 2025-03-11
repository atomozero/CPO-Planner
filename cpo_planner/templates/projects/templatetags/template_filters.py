from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
def index(value, i):
    """Ottiene un elemento dalla lista tramite indice"""
    try:
        return value[i]
    except (IndexError, KeyError, TypeError):
        return None

@register.filter
def getattr(obj, attr):
    """Ottiene un attributo da un oggetto tramite nome"""
    try:
        return obj.__getattribute__(attr)
    except (AttributeError, ValueError):
        return None
