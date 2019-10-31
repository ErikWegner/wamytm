import datetime
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import FormView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from typing import List

from .models import TimeRange
from .forms import AddTimeRangeForm


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
            days = []
            for _ in range(5):
                days.append(0)
            collector[item.user] = {"days": days, "kind": item.kind}
        for d in range(item.start.weekday(), 1 + item.end.weekday()):
            collector[item.user]["days"][d] = item.kind
    result = []
    for user in collector:
        result.append({"user": user, "days": collector[user]["days"]})
    return result


def _prepareList1Data(events: List[TimeRange], start, end):
    lines = []
    users = []
    for day in range((end - start).days):
        lines.append({
            'day': start + datetime.timedelta(days=day)
        })
    for event in events:
        for day in range((event.end - event.start).days + 1):
            line_index = (event.start - start).days + day
            if event.user not in users:
                users.append(event.user)
            lines[line_index][event.user] = event
    for line in lines:
        cols = []
        for user in users:
            if user in line:
                cols.append(line[user])
                del(line[user])
            else:
                cols.append([])
        line['cols'] = cols
    return {'lines': lines, 'users': users}


def index(request):
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    days = []
    for weekday in range(5):
        days.append(monday + datetime.timedelta(days=weekday))
    timeranges_thisweek = _prepareWeekdata(TimeRange.objects.thisWeek())
    context = {
        'this_week': timeranges_thisweek,
        'days': days,
    }
    return render(request, 'wamytmapp/index.html', context)


@login_required
def add(request):
    if request.method == 'POST':
        form = AddTimeRangeForm(data=request.POST, user=request.user)
        if form.is_valid():
            time_range = form.get_time_range()
            time_range.save()
            return HttpResponseRedirect(reverse('wamytmapp:index'))
    else:
        form = AddTimeRangeForm(user=request.user)

    return render(request, 'wamytmapp/add.html', {'form': form})


def list1(request):
    start = request.GET.get('from')
    end = request.GET.get('to')
    events, start, end = TimeRange.objects.list1(start, end)
    viewdata = _prepareList1Data(events, start, end)
    return render(request, 'wamytmapp/list1.html', viewdata)