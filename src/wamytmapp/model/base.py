import datetime
from django.db import models, connection
from django.db.models.functions import Greatest, Least
from django.contrib.auth.models import User
from django.utils.translation import pgettext_lazy
from django_prometheus.models import ExportModelOperationsMixin
from django.core.serializers.json import DjangoJSONEncoder
from typing import Union, List, Tuple

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def user_display_name(user):
    #full_name = user.get_full_name()
    full_name = user.last_name + ", " + user.first_name
    return full_name if full_name != "" else user.username

def normalize_list(parents: Union[int, List[int]]) -> Tuple[int, ...]:
    if isinstance(parents, list):
        return tuple(parents)
    return (parents,)