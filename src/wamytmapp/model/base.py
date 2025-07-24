from django.db import models, connection
from django.db import close_old_connections
from django.contrib.auth.models import User
from django.utils.translation import pgettext_lazy
from django_prometheus.models import ExportModelOperationsMixin
from django.core.serializers.json import DjangoJSONEncoder
from typing import Union, List, Tuple
import datetime

def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]

def safe_db_query(query_func):
    """
    Wrapper to ensure database connections are properly managed in gevent environments.
    Closes old connections before executing the query function.
    """
    def wrapper(*args, **kwargs):
        close_old_connections()
        return query_func(*args, **kwargs)
    return wrapper

def user_display_name(user):
    full_name = user.last_name + ", " + user.first_name
    return full_name if full_name != "" else user.username

def normalize_list(parents: Union[int, List[int]]) -> Tuple[int, ...]:
    if isinstance(parents, list):
        return tuple(parents)
    return (parents,)

def get_children(org_units: List[any]):
    z = []
    c = {}
    for org_unit in org_units:
        if org_unit.parent is None:
            if org_unit.id not in c.keys():
                z.append(org_unit)
                c[org_unit.id] = []
        else:
            if org_unit.parent_id not in c.keys():
                z.append(org_unit.parent)
                c[org_unit.parent_id] = []
            c[org_unit.parent_id].append(org_unit)

    r = []
    for org_unit in z:
        if org_unit.parent is None:
            r.append((org_unit.id, org_unit.name))
        if org_unit.id in c and len(c[org_unit.id]) > 0:
            charr = []
            for child_org_unit in c[org_unit.id]:
                charr.append((child_org_unit.id, child_org_unit.name))
            r.append((org_unit.name, tuple(charr)))
    return r