import datetime
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponse
from django.views.generic import FormView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from typing import List

from .models import TimeRange, TeamMember
from .forms import AddTimeRangeForm, OrgUnitFilterForm, ProfileForm


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
            collector[item.user] = {"days": days}
        for d in range(item.start_trim.weekday(), 1 + item.end_trim.weekday()):
            collector[item.user]["days"][d] = item.kind
    result = []
    for user in collector:
        result.append({"user": user, "days": collector[user]["days"]})
    return result


def _prepareList1Data(events: List[TimeRange], start, end, businessDaysOnly=True):
    lines = []
    users = []
    week_is_even = True
    four_week_counter = 0
    for day_delta in range((end - start).days):
        day = start + datetime.timedelta(days=day_delta)
        weekday = day.weekday()
        if weekday == 0:
            four_week_counter = (four_week_counter + 1) % 4
            week_is_even = not week_is_even
        if businessDaysOnly and (weekday > 4):
            continue
        lines.append({
            'day': day,
            'week_is_even': week_is_even,
            'four_week_counter': four_week_counter,
            'start_of_week': weekday == 0
        })
    for event in events:
        for day in range((event.end_trim - event.start_trim).days + 1):
            line_index = (event.start_trim - start).days + day
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
    else:
        form = AddTimeRangeForm(user=request.user)

    return render(request, 'wamytmapp/add.html', {'form': form})


def list1(request):
    filterform = OrgUnitFilterForm(data=request.GET)
    orgunitparamvalue = None
    start = None
    end = None
    orgunit = None
    if filterform.is_valid():
        startparamvalue = filterform.cleaned_data['fd']
        start = datetime.datetime.strptime(
            startparamvalue, "%Y-%m-%d") if startparamvalue else None
        endparamvalue = filterform.cleaned_data['td']
        end = datetime.datetime.strptime(
            endparamvalue, "%Y-%m-%d") if endparamvalue else None
        orgunitparamvalue = filterform.cleaned_data['orgunit']
    orgunit = int(orgunitparamvalue) if orgunitparamvalue else None
    events, start, end = TimeRange.objects.list1(start, end, orgunit)
    viewdata = _prepareList1Data(events, start, end)
    viewdata['ouselect'] = filterform

    return render(request, 'wamytmapp/list1.html', viewdata)


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(data=request.POST, user=request.user)
        if form.is_valid():
            orgunit_id = form.cleaned_data['orgunit']
            try:
                teammember = TeamMember.objects.get(pk=request.user.id)
                teammember.orgunit_id = orgunit_id
                teammember.save()
                return HttpResponseRedirect(reverse('wamytmapp:index'))
            except ValidationError as e:
                for field in e.message_dict.keys():
                    for error in e.message_dict[field]:
                        form.add_error(field, error)
                # Do something based on the errors contained in e.message_dict.
                # Display them to a user, or handle them programmatically.
                pass
    else:
        form = ProfileForm(user=request.user)

    return render(request, 'wamytmapp/profile.html', {'form': form})
