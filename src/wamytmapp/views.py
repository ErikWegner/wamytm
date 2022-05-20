import csv
import datetime
#import cProfile
#import pstats
from django_ical.views import ICalFeed
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, PermissionDenied, SuspiciousOperation
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import get_language_from_request
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import FormView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from typing import List

from .config import RuntimeConfig
from .models import my_custom_sql, TimeRange, TeamMember, query_events_timeranges_in_week, query_events_list1, user_display_name, TimeRangeManager
from .forms import AddTimeRangeForm, OrgUnitFilterForm, ProfileForm, FrontPageFilterForm, ConflictCheckForm
from .serializers import TimeRangeSerializer
from .models import OrgUnit, OMS, ODB_MITARBEITER2STRUKT, AllDayEvent


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
            daydata = item.data
            daydata['k'] = item.kind_with_details()
            collector[item.user]["days"][d] = daydata
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
            if event.user in line:
                if 'partial' not in event.data or 'partial' not in line[event.user].data:
                    continue

                if 'desc' in line[event.user].data or 'desc' in event.data:
                    if 'desc' not in line[event.user].data:
                       line[event.user].data['desc'] = event.data['desc']
                    else:
                        if line[event.user].data['partial'] == 'f' and event.data['partial'] == 'a':
                            line[event.user].data['desc'] = line[event.user].data['desc'] + ("; " + event.data['desc']) if 'desc' in event.data else ''
                        elif line[event.user].data['partial'] == 'a' and event.data['partial'] == 'f':
                            line[event.user].data['desc'] = ((event.data['desc'] +"; ") if 'desc' in event.data else '') + line[event.user].data['desc']

                if line[event.user].kind == event.kind:
                    del line[event.user].data[TimeRange.DATA_PARTIAL]
                    continue

                if line[event.user].data['partial'] == 'f' and event.data['partial'] == 'a':
                    if line[event.user].kind != event.kind:
                        line[event.user].kind = line[event.user].kind + event.kind
                elif line[event.user].data['partial'] == 'a' and event.data['partial'] == 'f':
                    if line[event.user].kind != event.kind:
                        line[event.user].kind = event.kind + line[event.user].kind

            else:
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


@xframe_options_exempt
def index(request):
    tempdict = request.GET.copy()

    if request.user is not None and request.user.is_authenticated and 'orgunit' not in request.GET:
        tempdict['orgunit'] = OMS.objects.getORG_ID(request.user.id).m2o_org_id

    filterform = FrontPageFilterForm(tempdict)

    if filterform.is_valid():
        orgunitparamvalue = filterform.cleaned_data['orgunit']

    weekdelta = filterform.cleaned_data['weekdelta']
    orgunit = int(orgunitparamvalue) if orgunitparamvalue else None
    usersStr = filterform.cleaned_data['users'] if 'users' in filterform.cleaned_data else None

    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday() - weekdelta * 7)
    days = []
    #users = usersStr.split(',') if usersStr else None

    for weekday in range(5):
        days.append(DayHeader(monday + datetime.timedelta(days=weekday)))

    alldayevents = AllDayEvent.objects.eventsInRange(monday, monday + datetime.timedelta(days=4))

    #timeranges, alldayevents = query_events_timeranges_in_week(day_of_week=monday, orgunit=orgunit, users=users)
    #timeranges_thisweek = _prepareWeekdata(timeranges)

    meins = my_custom_sql(orgid=orgunit, day_of_week=monday)

    for alldayevent in alldayevents:
        for dh in days:
            if dh.day == alldayevent.day:
                dh.allday = alldayevent

    context = {
        'meins': meins,
        'days': days,
        'trc': RuntimeConfig.TimeRangeViewsLegend,
        'weekdelta': weekdelta,
        'filterform': filterform,
    }
    context['embeded'] = 'embed' in request.GET and request.GET['embed'] == '1'
    if usersStr:
        context['users'] = usersStr

    return render(request, 'wamytmapp/index.html', context)


@login_required
def add(request):
    def handle_overlaps(form: AddTimeRangeForm):
        if form.cleaned_data['overlap_actions'] is None or form.cleaned_data['overlap_actions'] == "":
            return
        start = form.cleaned_data['start']
        end = form.cleaned_data['end'] if form.cleaned_data['end'] is not None else start
        kind = form.cleaned_data['kind']
        part = form.cleaned_data['part_of_day']
        overlaps = TimeRange.objects.overlapResolution(
            start,
            end,
            form.cleaned_data['user_id'],
            kind,
            part
            )
        overlaps_map = {}
        for m in overlaps['mods']:
            overlaps_map[m['item']['id']] = m['res']
        form_overlap_map = form.cleaned_data['overlap_actions']
        for f in form_overlap_map:
            fp = f.split(':')
            if len(fp) != 2:
                raise SuspiciousOperation()
            action = fp[1].lower()
            itemid = int(fp[0])
            if not itemid in overlaps_map or overlaps_map[itemid] != action:
                raise SuspiciousOperation()
            del(overlaps_map[itemid])
            if action == TimeRangeManager.OVERLAP_DELETE:
                TimeRange.objects.get(id=itemid).delete()
            elif action == TimeRangeManager.OVERLAP_NEW_END:
                item = TimeRange.objects.get(id=itemid)
                item.end = start + datetime.timedelta(days=-1)
                item.save()
            elif action == TimeRangeManager.OVERLAP_NEW_START:
                item = TimeRange.objects.get(id=itemid)
                item.start = end + datetime.timedelta(days=1)
                item.save()
            elif action == TimeRangeManager.OVERLAP_SPLIT:
                prev_item = TimeRange.objects.get(id=itemid)
                next_item = TimeRange.objects.get(id=itemid)
                next_item.pk = None
                prev_item.end = start + datetime.timedelta(days=-1)
                next_item.start = end + datetime.timedelta(days=1)
                prev_item.save()
                next_item.save()

    if request.method == 'POST':
        form = AddTimeRangeForm(data=request.POST, user=request.user)
        if form.is_valid():
            time_range = form.get_time_range()
            try:
                time_range.full_clean()
                handle_overlaps(form)
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


@xframe_options_exempt
def list1(request):
    filterformvalues = request.GET.copy()
    if request.user is not None and request.user.is_authenticated and 'orgunit' not in filterformvalues:
        #mit_id = OMS.objects.filter(user=request.user.id)
        M2O_ORG_ID = OMS.objects.getORG_ID(request.user.id)
        if M2O_ORG_ID is not None:
            filterformvalues['orgunit'] = M2O_ORG_ID.m2o_org_id

        #tm = TeamMember.objects.filter(pk=request.user.id)
        # if tm.exists():
            #filterformvalues['orgunit'] = tm.first().orgunit_id

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
    viewdata['orgunit'] = 0 if orgunit is None else orgunit
    viewdata['trc'] = RuntimeConfig.TimeRangeViewsLegend
    viewdata['embeded'] = 'embed' in request.GET and request.GET['embed'] == '1'

    return render(request, 'wamytmapp/list1.html', viewdata)


def weekCSV(request):
    weekdelta = int(request.GET['weekdelta']) if "weekdelta" in request.GET else 0
    timeRangeFilter = request.GET['kind'] if 'kind' in request.GET else None

    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday() - weekdelta * 7)
    timeranges, _ = query_events_timeranges_in_week(monday)
    print(timeranges)
    users = []
    for timerange in timeranges:
        if timerange.user in users:
            continue
        if timeRangeFilter is not None and timerange.kind != timeRangeFilter:
            continue
        users.append(timerange.user)

    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = F'attachment; filename="korporator-{monday}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow(['KID', 'Vorname', 'Nachname', 'E-Mail'])
    for user in users:
        writer.writerow([user.username, user.first_name,user.last_name, user.email])

    return response


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


def conflict_check(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()
    if request.method == 'POST':
        form = ConflictCheckForm(data=request.POST, request=request)
        if not form.is_valid():
            return JsonResponse(form.errors, status=400)
        responseData = TimeRange.objects.overlapResolution(
            form.cleaned_data['start'],
            form.cleaned_data['end'],
            form.cleaned_data['uid'],
            form.cleaned_data['kind'],
            form.cleaned_data['part']
            )
        return JsonResponse(responseData)
    return HttpResponseBadRequest()


class TeamFeed(ICalFeed):
    product_id = '-//example.com//Example//EN'
    timezone = 'UTC'
    file_name = "event.ics"

    def items(self, obj):
        orgunit = obj['orgunit'] if obj['orgunit'] > 0 else None
        today = datetime.date.today()
        startdate = today - datetime.timedelta(weeks=4)
        enddate = today + datetime.timedelta(weeks=12)
        (events, _), _, _ = query_events_list1(startdate, enddate, orgunit)
        return events

    def get_object(self, request, *args, **kwargs):
        return {'orgunit': kwargs['orgunit']}

    def item_guid(self, item):
        return F"{item.id}@wamytm"

    def item_title(self, item):
        username = user_display_name(item.user)
        kind = RuntimeConfig.TimeRangeViewsLegend[item.kind_with_details()]
        return F"{username} ({kind})"

    def item_description(self, item):
        return ""

    def item_start_datetime(self, item):
        return item.start

    def item_end_datetime(self, item):
        return item.end

    def item_link(self, item):
        return reverse('wamytmapp:list1') + F"?orgunit={item.orgunit_id}"
