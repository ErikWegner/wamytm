from django.http import HttpResponse
from django.template import loader
from typing import List

from .models import TimeRange


def _prepareWeekdata(weekdata: List[TimeRange]):
    """
        Prepare a week representation.

        It is a list of objects, each with:
        - user
        - days
    """
    collector = {}
    for item in weekdata:
        if item.user not in collector:
            daysinit = TimeRange.ABSENT if item.kind == TimeRange.PRESENT else TimeRange.PRESENT
            days = []
            for _ in range(5):
                days.append(daysinit) 
            collector[item.user] = {"days": days, "kind": item.kind}
        for d in range(item.start.weekday(), 1 + item.end.weekday()):
            collector[item.user]["days"][d] = item.kind
    result = []
    for user in collector:
        result.append({"user": user, "days": collector[user]["days"]})
    return result


def index(request):
    timeranges_thisweek = _prepareWeekdata(TimeRange.objects.thisWeek())
    template = loader.get_template('wamytmapp/index.html')
    context = {
        'this_week': timeranges_thisweek,
    }
    return HttpResponse(template.render(context, request))
