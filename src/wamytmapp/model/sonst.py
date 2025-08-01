from .base import *
from .Timerange import TimeRange
from .OrgUnit import OrgUnit
from .virtualteam import ma2vt
from .ODB import OMS

class AllDayEventsManager(models.Manager):
    def eventsInRange(self, von: datetime.date, end: datetime.date):
        """
            Return all TimeRange objects that overlap with the
            start and end date
        """
        query = super().get_queryset().filter(
            day__lte=end,
            day__gte=von)

        return query


class AllDayEvent(models.Model):
    description = models.TextField(
        max_length=100,
        verbose_name=pgettext_lazy('AllDayEvent', 'description')
    )
    day = models.DateField(
        verbose_name=pgettext_lazy('AllDayEvent', 'day')
    )

    objects = AllDayEventsManager()

    class Meta:
        verbose_name = pgettext_lazy('Models', 'all day event')
        verbose_name_plural = pgettext_lazy('Models', 'all day events')
        indexes = [
            models.Index(fields=['day']),
        ]

    def __str__(self):
        return f"All day event on {self.day}: {self.description}"

class KIND(models.Model):
    kind = models.CharField(choices=TimeRange.KIND_CHOICES, max_length=1,primary_key=True)
    wertung = models.SmallIntegerField(blank=True, null=True)

class TeamMemberManager(models.Manager):
    pass


class TeamMember(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True,)
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, null=True)
    objects = TeamMemberManager()

    def __str__(self):
        return f"{self.user} ({self.orgunit})"
    
def query_events_timeranges(
        start: datetime.date,
        end: datetime.date,
        orgunits: List[OrgUnit] = None,
        users: List[str] = None
):
    alldayevents = AllDayEvent.objects.eventsInRange(start, end)
    timeranges = TimeRange.objects.eventsInRange(start, end, orgunits=orgunits, users=users)
    return timeranges, alldayevents

def query_events_timeranges2(
        start: datetime.date,
        end: datetime.date,
        users: List[int] = None,
        orgunits: List[int] = None
):
    alldayevents = AllDayEvent.objects.eventsInRange(start, end)
    timeranges = TimeRange.objects.eventsInRange(start, end)
    if users is not None:
        timeranges = timeranges.filter(user__in=users)
    if orgunits is not None:
        team_members = OMS.objects.queryAllTeammember(orgunits)
        user_ids = [tm.id for tm in team_members]  # Use list comprehension instead of map/lambda
        timeranges = timeranges.filter(user__in=user_ids)
            
    return timeranges, alldayevents


def query_events_timeranges_in_week(
    day_of_week: datetime.date = None,
    orgunit: OrgUnit = None,
    users: List[str] = None
):
    """
        Return all TimeRange objects that start during this week or
        that end during this week.
    """
    today = datetime.date.today() if day_of_week is None else day_of_week
    monday = today - datetime.timedelta(days=today.weekday())
    friday = monday + datetime.timedelta(days=4)
    orgunits = OrgUnit.objects.listDescendants(
        orgunit) if orgunit is not None else None
    return query_events_timeranges(monday, friday, orgunits=orgunits, users=users)


def query_events_list1(start, end, orgunit=0):
    if start is None:
        start = datetime.date.today()
    if end is None or end < start:
        end = start + datetime.timedelta(days=100)

    orgunit = 0 if orgunit is None else orgunit
    
    if orgunit >= 0:
        orgunits =  [x.id for x in OMS.objects.queryDescendants([orgunit])]
        timeranges, alldayevents = query_events_timeranges2(start=start, end=end, orgunits=orgunits)
        timeranges = list(timeranges)
        alldayevents = list(alldayevents)
        ret = ((timeranges, alldayevents), start, end)
    else:
        userlist = ma2vt.objects.get_users(orgunit)
        timeranges, alldayevents = query_events_timeranges2(start=start, end=end, users=userlist)
        timeranges = list(timeranges)
        alldayevents = list(alldayevents)
        ret = ((timeranges, alldayevents), start, end)
    return ret