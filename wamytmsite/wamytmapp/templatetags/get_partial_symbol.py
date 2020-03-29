from ..models import TimeRange
from django import template

register = template.Library()


@register.filter
def get_partial_symbol(value):
    if TimeRange.DATA_PARTIAL not in value:
        return ''
    if value[TimeRange.DATA_PARTIAL] == 'f':
        return ' 🕗'
    if value[TimeRange.DATA_PARTIAL] == 'a':
        return ' 🕑'
    return ''
