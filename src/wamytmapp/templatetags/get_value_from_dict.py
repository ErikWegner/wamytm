from django import template
register = template.Library()

@register.filter('get_value_from_dict')
def get_value_from_dict(dict_data, key):
    if key:
        ret = dict_data.get(key)
        if ret == None:
            return ''
        else:
            return ret
