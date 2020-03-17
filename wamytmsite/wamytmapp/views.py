import datetime
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.views.generic import FormView
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.utils.translation import get_language_from_request
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import List

from .models import TimeRange, TeamMember, query_events_timeranges_in_week, query_events_list1, user_display_name
from .forms import AddTimeRangeForm, OrgUnitFilterForm, ProfileForm
from .serializers import TimeRangeSerializer

class DayHeader:
    def __init__(self, day: datetime.date):
        self.day = day
        self.allday = False
        pass

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
        result.append({
            "user": user,
            "username": user_display_name(user),
            "days": collector[user]["days"]})
    return result


def _prepareList1Data(events: List[TimeRange], start, end, businessDaysOnly=True):
    lines = []
    users = []
    week_is_even = True
    four_week_counter = 0
    # prepare all rows
    for day_delta in range((end - start).days + 1):
        day = start + datetime.timedelta(days=day_delta)
        weekday = day.weekday()
        if weekday == 0:
            four_week_counter = (four_week_counter + 1) % 4
            week_is_even = not week_is_even
        if businessDaysOnly and (weekday > 4):
            continue
        lines.append({
            'day': DayHeader(day),
            'week_is_even': week_is_even,
            'four_week_counter': four_week_counter,
            'start_of_week': weekday == 0
        })
    for event in events:
        for line in lines:
            dh = line['day']
            day = dh.day
            # check if the day of the row is in the duration of the event
            if day < event.start or day > event.end:
                continue
            # record any user with an event
            if event.user not in users:
                users.append(event.user)
                event.user.display_name = user_display_name(event.user)
            # and the event to the row
            line[event.user] = event
    for line in lines:
        # prepare columns for every recorded user
        cols = []
        for user in users:
            if user in line:
                # append the event to the columns of the row
                cols.append(line[user])
                # remove unnecessary data from the final view data
                del(line[user])
            else:
                cols.append([])
        line['cols'] = cols
    return {'lines': lines, 'users': users}


def index(request):
    weekdelta = int(request.GET['weekdelta']) if "weekdelta" in request.GET else 0
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday() - weekdelta * 7)
    days = []
    for weekday in range(5):
        dh = DayHeader(monday + datetime.timedelta(days=weekday))
        days.append(dh)
    timeranges, alldayevents = query_events_timeranges_in_week(monday)
    for alldayevent in alldayevents:
        for dh in days:
            if dh.day == alldayevent.day:
                dh.allday = alldayevent
    timeranges_thisweek = _prepareWeekdata(timeranges)
    context = {
        'this_week': timeranges_thisweek,
        'days': days,
        'trc': TimeRange.VIEWS_LEGEND,
        'weekdelta': weekdelta
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
    language = get_language_from_request(request)
    if language is not None and language.startswith("de"):
        form.fields['start'].widget.attrs['data-date-language'] = 'de'
        form.fields['end'].widget.attrs['data-date-language'] = 'de'

    return render(request, 'wamytmapp/add.html', {'form': form})


def list1(request):
    filterformvalues = request.GET.copy()
    if request.user is not None and request.user.is_authenticated and 'orgunit' not in filterformvalues:
        filterformvalues['orgunit'] = TeamMember.objects.get(
                pk=request.user.id).orgunit_id
    filterform = OrgUnitFilterForm(filterformvalues)
    orgunitparamvalue = None
    start = None
    end = None
    orgunit = None
    if filterform.is_valid():
        startparamvalue = filterform.cleaned_data['fd']
        start = datetime.datetime.strptime(
            startparamvalue, "%Y-%m-%d").date() if startparamvalue else None
        endparamvalue = filterform.cleaned_data['td']
        end = datetime.datetime.strptime(
            endparamvalue, "%Y-%m-%d").date() if endparamvalue else None
        orgunitparamvalue = filterform.cleaned_data['orgunit']
    orgunit = int(orgunitparamvalue) if orgunitparamvalue else None
    (events, alldayevents), start, end = query_events_list1(start, end, orgunit)
    viewdata = _prepareList1Data(events, start, end)
    for alldayevent in alldayevents:
        for line in viewdata['lines']:
            dh = line['day']
            if dh.day == alldayevent.day:
                dh.allday = alldayevent
    viewdata['ouselect'] = filterform
    viewdata['trc'] = TimeRange.VIEWS_LEGEND

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

class TimeRangesList(APIView):
    permission_classes = [IsAuthenticated]

    """
    List TimeRange objects
    """
    def get(self, request, format=None):
        timerangeItems = TimeRange.objects.all()
        serializer = TimeRangeSerializer(timerangeItems, many=True)
        return Response(serializer.data)
