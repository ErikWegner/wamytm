from ..models import TimeRange
from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def get_partial_symbol(value):
    if TimeRange.DATA_PARTIAL not in value:
        return ''
    if value[TimeRange.DATA_PARTIAL] == 'f':
        return mark_safe(' <span class="partial-f">🕗</span>')
    if value[TimeRange.DATA_PARTIAL] == 'a':
        return mark_safe(' <span class="partial-a">🕑</span>')
    return ''
