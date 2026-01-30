import datetime
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_exempt

from ..model.sonst import AllDayEvent
from ..model.ODB import OMS, mv_odb_org, my_custom_sql2
from ..config import RuntimeConfig
from ..forms import FrontPageFilterForm


class DayHeader:
    def __init__(self, day: datetime.date):
        self.day = day
        self.allday = False
        pass


@xframe_options_exempt
def index(request):

    tempdict = request.GET.copy()

    if request.user is not None and request.user.is_authenticated and 'orgunit' not in request.GET and 'users' not in request.GET: 
        m2o_org_id = OMS.objects.getORG_ID(request.user.id)
        tempdict['orgunit'] = m2o_org_id.m2o_org_id if m2o_org_id is not None else None
    else:
        m2o_org_id = None

    filterform = FrontPageFilterForm(tempdict)

    if filterform.is_valid():
        orgunitparamvalue = filterform.cleaned_data['orgunit']
        weekdelta = filterform.cleaned_data['weekdelta'] or 0
        usersStr = filterform.cleaned_data.get('users')
    else:
        orgunitparamvalue = None
        weekdelta = 0
        usersStr = None
    
    # Ensure weekdelta is a valid integer and within reasonable bounds
    if weekdelta is None:
        weekdelta = 0
    
    # More restrictive bounds to prevent Oracle date issues
    if weekdelta < -100 or weekdelta > 100:  # roughly ±2 years
        weekdelta = 0
    
    orgunit = int(orgunitparamvalue) if orgunitparamvalue else 0

    today = datetime.date.today()
    
    # Calculate monday with safer approach
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
    
    days = []
    users = usersStr.split(',') if usersStr else None

    for weekday in range(5):
        days.append(DayHeader(monday + datetime.timedelta(days=weekday)))

    alldayevents = AllDayEvent.objects.eventsInRange(monday, monday + datetime.timedelta(days=4))

    for alldayevent in alldayevents:
        for dh in days:
            if dh.day == alldayevent.day:
                dh.allday = alldayevent

    orgunits = mv_odb_org.objects.getORGS4FILTER()

    context = {
        'meins': my_custom_sql2(orgid=orgunit, day_of_week=monday, users=users),
        'orgunit': list(filter(lambda x: (x['ID'] > 0),orgunits)),
        'orgunit_vt': list(filter(lambda x: (x['ID'] < 0),orgunits)),
        'orgunit_initial': m2o_org_id.m2o_org_id if m2o_org_id is not None else str(orgunit or '0'),
        'days': days,
        'trc': RuntimeConfig.TimeRangeViewsLegend,
        'weekdelta': weekdelta,
        'filterform': filterform,
        'current_user_name': f"{request.user.last_name}, {request.user.first_name} ({request.user.username.upper()[1:]})".strip() if request.user.is_authenticated else None,
    }
    context['embeded'] = 'embed' in request.GET and request.GET['embed'] == '1'
    if usersStr:
        context['users'] = usersStr

    return render(request, 'wamytmapp/index.html', context)