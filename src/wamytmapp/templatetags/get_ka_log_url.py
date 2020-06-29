from django import template
from django.contrib.admin.models import LogEntry
from django.contrib.admin.utils import quote
from django.urls import NoReverseMatch, reverse
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def get_ka_log_url(logentry):
    if logentry.content_type and logentry.object_id:
        url_name = 'admin:%s_%s_change' % (
            logentry.content_type.app_label, logentry.content_type.model)
        try:
            return reverse(url_name, args=(quote(logentry.object_id),), current_app='ka')
        except NoReverseMatch:
            pass
    return None
