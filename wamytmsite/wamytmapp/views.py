import datetime
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import FormView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from typing import List

from .models import TimeRange
from .forms import AddTimeRangeForm, OrgUnitFilterForm


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


def _prepareList1Data(events: List[TimeRange], start, end, businessDaysOnly=True):
    lines = []
    users = []
    for day_delta in range((end - start).days):
        day = start + datetime.timedelta(days=day_delta)
        weekday = day.weekday()
        if businessDaysOnly and (weekday > 4):
            continue
        lines.append({
            'day': day,
            'start_of_week': weekday == 0
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
            try:
                time_range.full_clean()
                time_range.save()
                return HttpResponseRedirect(reverse('wamytmapp:index'))
            except ValidationError as e:
                for field in e.message_dict.keys():
                    for error in e.message_dict[field]:
                        form.add_error(field, error)
                # Do something based on the errors contained in e.message_dict.
                # Display them to a user, or handle them programmatically.
                pass
    else:
        form = AddTimeRangeForm(user=request.user)

    return render(request, 'wamytmapp/add.html', {'form': form})


def list1(request):
    start = request.GET.get('from')
    end = request.GET.get('to')
    orgunitparamvalue = request.GET.get('orgunit')
    orgunit = int(orgunitparamvalue) if orgunitparamvalue else None
    events, start, end = TimeRange.objects.list1(start, end, orgunit)
    viewdata = _prepareList1Data(events, start, end)
    viewdata['ouselect'] = OrgUnitFilterForm(data=request.GET)

    return render(request, 'wamytmapp/list1.html', viewdata)
