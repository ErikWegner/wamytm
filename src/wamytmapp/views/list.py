import csv
import datetime
from django_ical.views import ICalFeed
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.clickjacking import xframe_options_exempt
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..model.Timerange import TimeRange
from ..model.sonst import query_events_timeranges_in_week, query_events_list1, user_display_name
from ..model.ODB import OMS, mv_odb_org, my_custom_sql3
from ..config import RuntimeConfig
from ..forms import OrgUnitFilterForm, ConflictCheckForm
from ..serializers import TimeRangeSerializer


@xframe_options_exempt
def list2(request):
    filterformvalues = request.GET.copy()
    if request.user is not None and request.user.is_authenticated and 'orgunit' not in filterformvalues:
        M2O_ORG_ID = OMS.objects.getORG_ID(request.user.id)
        if M2O_ORG_ID is not None:
            filterformvalues['orgunit'] = M2O_ORG_ID.m2o_org_id

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

    if start is None:
        start = datetime.date.today()
    if end is None or end < start:
        end = start + datetime.timedelta(days=100)

    orgunit = int(orgunitparamvalue) if orgunitparamvalue else None
    #alldayevents = AllDayEvent.objects.eventsInRange(start, end)

    data = my_custom_sql3(start, end, orgunit)
    viewdata = {}
    viewdata['data'] = data
    viewdata['header'] = [user['USERNAME'] for user in data if user.get('N', None) == 1 and 'USERNAME' in user]
    viewdata['ouselect'] = filterform
    viewdata['orgunit'] = 0 if orgunit is None else orgunit
    viewdata['orgunit_initial'] = 0 if orgunit is None else orgunit
    viewdata['orgunit_filter'] = mv_odb_org.objects.getORGS4FILTER()
    viewdata['trc'] = RuntimeConfig.TimeRangeViewsLegend
    viewdata['embeded'] = 'embed' in request.GET and request.GET['embed'] == '1'
    
    return render(request, 'wamytmapp/list2.html', viewdata)

def weekCSV(request):
    try:
        weekdelta = int(request.GET['weekdelta']) if "weekdelta" in request.GET else 0
    except (ValueError, TypeError):
        weekdelta = 0
    timeRangeFilter = request.GET['kind'] if 'kind' in request.GET else None

    today = datetime.date.today()
    
    # More restrictive bounds to prevent Oracle date issues
    if weekdelta < -100 or weekdelta > 100:  # roughly ±2 years
        weekdelta = 0
    
    try:
        # Calculate the target date more safely
        target_days = today.weekday() - weekdelta * 7
        monday = today - datetime.timedelta(days=target_days)
        
        # Ensure the date is within Oracle's valid range
        min_oracle_date = datetime.date(100, 1, 1)  # More conservative minimum
        max_oracle_date = datetime.date(9000, 12, 31)  # More conservative maximum
        
        if monday < min_oracle_date or monday > max_oracle_date:
            # Reset to current week if outside valid range
            monday = today - datetime.timedelta(days=today.weekday())
            
    except (OverflowError, ValueError):
        # If any date calculation fails, reset to current week
        monday = today - datetime.timedelta(days=today.weekday())
    
    timeranges, _ = query_events_timeranges_in_week(monday)
   
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


# Profile functionality removed - was dependent on TeamMember model
# @login_required
# def profile(request):
#     # This functionality has been removed as it depended on the TeamMember model


class TimeRangesList(APIView):
    permission_classes = [IsAuthenticated]

    """
    List TimeRange objects
    """

    def get(self, request, format=None):
        # Add filtering and limit to prevent timeouts
        # Get recent timeranges only, limit to 1000 records
        timerangeItems = TimeRange.objects.all().order_by('-id')[:1000]
        serializer = TimeRangeSerializer(timerangeItems, many=True)
        return Response(serializer.data)

def getorgid(request):
    if not request.user.is_authenticated:
        raise PermissionDenied()

    if request.method == 'POST':
        r = { }
        r['org_id'] = OMS.objects.getORG_ID(request.POST['uid']).m2o_org_id

        return JsonResponse(r)
    return HttpResponseBadRequest()

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
        responseData['org_id'] = OMS.objects.getORG_ID(form.cleaned_data['uid']).m2o_org_id
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
        return item.von

    def item_end_datetime(self, item):
        return item.bis

    def item_link(self, item):
        return reverse('wamytmapp:list2') + F"?orgunit={item.org_id}"
