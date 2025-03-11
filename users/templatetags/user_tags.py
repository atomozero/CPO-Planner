# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def user_avatar_svg(size=60):
    """
    Restituisce un SVG di una presa elettrica da usare come avatar predefinito.
    """
    svg = f'''
    <svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="11.5" fill="#f8f9fc" stroke="#4e73df"/>
        <path d="M8 11V7H16V11" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M12 11V17" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M6 17H18" stroke="#4e73df" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    '''
    return mark_safe(svg)