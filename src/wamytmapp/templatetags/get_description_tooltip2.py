from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_description_tooltip2(value):
    if not value or not isinstance(value, dict) or 'desc' not in value:
        return ''
    description = value['desc']
    if description is None:
        return ''
    description = escape(description)
    return mark_safe(f'<span data-toggle="tooltip" title="{description}">💬</span>')
