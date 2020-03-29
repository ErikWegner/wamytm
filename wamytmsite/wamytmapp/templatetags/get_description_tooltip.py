from ..models import TimeRange
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_description_tooltip(value):
    if TimeRange.DATA_DESCRIPTION not in value:
        return ''
    description = value[TimeRange.DATA_DESCRIPTION]
    if description == "":
        return ''
    description = escape(description)
    return mark_safe(f'<span data-toggle="tooltip" title="{description}">💬</span>')
