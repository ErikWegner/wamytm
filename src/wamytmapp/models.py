import datetime

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.functions import Greatest, Least
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy
from simple_history.models import HistoricalRecords
from typing import List


class OrgUnitManager(models.Manager):
    def selectListItems(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        return toplevel

    def selectListItemsWithAllChoice(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        toplevel.insert(0, ("", pgettext_lazy('OrgUnitManager', "All")))
        return toplevel

    def queryDescendants(self, parents):
        parentslist = tuple(parents if type(parents) is list else [parents])
        if len(parentslist) == 0:
            return list()
        qu = super().raw('''
        WITH RECURSIVE ou(id, parent_id) AS (
            SELECT id, parent_id
            FROM wamytmapp_orgunit
            WHERE id in %s
        UNION ALL
            SELECT t2.id, t2.parent_id
            FROM wamytmapp_orgunit AS t2, ou AS t1
            WHERE t2.parent_id = t1.id
        )
        SELECT DISTINCT id FROM ou
        ''', params=[parentslist])
        return list(qu)

    def queryParents(self, children):
        idlist = children if type(children) is list else [children]
        qu = super().raw('''
        WITH RECURSIVE ou(id, parent_id) AS (
            SELECT id, parent_id
            FROM wamytmapp_orgunit
            WHERE id in (%s)
        UNION ALL
            SELECT t2.id, t2.parent_id
            FROM wamytmapp_orgunit AS t2, ou AS t1
            WHERE t2.id = t1.parent_id
        )
        SELECT DISTINCT id FROM ou
        ''', idlist)
        return list(qu)

    def listDescendants(self, parent_id):
        all_org_units = super().all()
        descendants = collect_descendents(all_org_units, parent_id)
        descendants.insert(0, parent_id)
        return descendants


class OrgUnit(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True)
    delegates = models.ManyToManyField(
        User,
        through='OrgUnitDelegate'
    )

    objects = OrgUnitManager()

    class Meta:
        ordering = ['name']
        verbose_name = pgettext_lazy('Models', 'Organizational unit')
        verbose_name_plural = pgettext_lazy('Models', 'Organizational units')

    def __str__(self):
        return self.name


class TeamMemberManager(models.Manager):
    pass


class TeamMember(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True,)
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, null=True)
    objects = TeamMemberManager()

    def __str__(self):
        return f"{self.user} ({self.orgunit})"


@receiver(post_save, sender=User)
def create_teammember(sender, instance, created, **kwargs):
    if created:
        TeamMember.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_teammember(sender, instance, **kwargs):
    if hasattr(instance, 'teammember'):
        instance.teammember.save()


class TimeRangeManager(models.Manager):
    OVERLAP_NEW_END = 'end'
    OVERLAP_NEW_START = 'beg'
    OVERLAP_SPLIT = 'spl'
    OVERLAP_DELETE = 'del'

    def list1(self, start, end, orgunit=None):
        if start is None:
            start = datetime.date.today()
        if end is None or end < start:
            end = start + datetime.timedelta(days=100)
        orgunits = OrgUnit.objects.listDescendants(
            orgunit) if orgunit is not None else None
        return (self.eventsInRange(start, end, orgunits), start, end)

    def thisWeek(self):
        """
            Return all TimeRange objects that start during this week or
            that end during this week.
        """
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        friday = monday + datetime.timedelta(days=4)
        return self.eventsInRange(monday, friday)

    def eventsInRange(self,
                      start: datetime.date,
                      end: datetime.date,
                      orgunits: List[OrgUnit] = None,
                      userid: int = None,
                      users: List[str] = None):
        """
            Return all TimeRange objects that overlap with the
            start and end date
        """
        query = super().get_queryset(
        ).filter(
            start__lte=end,
            end__gte=start
        ).annotate(
            start_trim=Greatest(
                'start', start, output_field=models.DateField(default=datetime.datetime.now(tz=timezone.utc))),
            end_trim=Least(
                'end', end, output_field=models.DateField(default=datetime.datetime.now(tz=timezone.utc)))
        ).order_by(
            'user__last_name',
            'user__first_name',
            'user__username'
        )

        if orgunits is not None:
            query = query.filter(orgunit__in=orgunits)

        if userid is not None:
            query = query.filter(user__id=userid)

        if users is not None and len(users) > 0:
            users_qs = User.objects.filter(username__in=users)
            query = query.filter(user__in=users_qs)

        return query

    def overlapResolution(self, start: datetime.date, end: datetime.date, userid: int):
        r = {'mods': []}

        overlapping_items = self.eventsInRange(start, end, userid=userid)
        for item in overlapping_items:
            mod = {'res': None, 'item': item.buildConflictJsonStructure()}
            if item.start >= start and item.end <= end:
                mod['res'] = TimeRangeManager.OVERLAP_DELETE
            elif item.start < start and item.end > end:
                mod['res'] = TimeRangeManager.OVERLAP_SPLIT
            elif item.start < start:
                mod['res'] = TimeRangeManager.OVERLAP_NEW_END
            elif item.end > end:
                mod['res'] = TimeRangeManager.OVERLAP_NEW_START
            r['mods'].append(mod)

        return r


class TimeRange(models.Model):
    DATA_KINDDETAIL = 'kinddetail'
    DATA_DESCRIPTION = 'desc'
    DATA_PARTIAL = 'partial'
    ABSENT = 'a'
    PRESENT = 'p'
    MOBILE = 'm'
    KIND_CHOICES = [
        (ABSENT, pgettext_lazy('TimeRangeChoice', 'absent')),
        (PRESENT, pgettext_lazy('TimeRangeChoice', 'present')),
        (MOBILE, pgettext_lazy('TimeRangeChoice', 'mobile')),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name=pgettext_lazy('TimeRange', 'User'))
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE,
                                verbose_name=pgettext_lazy('TimeRange', 'Organizational unit'))
    start = models.DateField(verbose_name=pgettext_lazy('TimeRange', 'Start'))
    end = models.DateField(
        blank=True, verbose_name=pgettext_lazy('TimeRange', 'End'))
    kind = models.CharField(choices=KIND_CHOICES, max_length=1, default=ABSENT,
                            verbose_name=pgettext_lazy('TimeRange', 'Kind of time range'))
    data = models.JSONField(encoder=DjangoJSONEncoder)
    history = HistoricalRecords()

    objects = TimeRangeManager()

    class Meta:
        verbose_name = pgettext_lazy('Models', 'time range')
        verbose_name_plural = pgettext_lazy('Models', 'time ranges')
        indexes = [
            models.Index(fields=['start', 'end']),
            models.Index(fields=['orgunit', 'start', 'end']),
        ]

    def clean(self):
        if self.end is not None and self.end < self.start:
            raise ValidationError(
                {'end': pgettext_lazy('Models', 'End date may not be before start date.')})

    def save(self, *args, **kwargs):
        if self.end == None:
            self.end = self.start
        super().save(*args, **kwargs)

    def getDayCount(self):
        return (self.end - self.start).days

    def __str__(self):
        s = pgettext_lazy('TimeRangeStr', "TimeRange")
        return str(format_lazy('{s}({start}, {end})', s=s, start=self.start, end=self.end))

    def kind_with_details(self):
        r = self.kind
        if self.data and TimeRange.DATA_KINDDETAIL in self.data:
            r = r + self.data[TimeRange.DATA_KINDDETAIL]
        return r

    def buildConflictJsonStructure(self):

        return {
            'id': self.id,
            'start': (self.start if isinstance(self.start, datetime.date) else self.start.date()).strftime('%Y-%m-%d'),
            'end': (self.end if isinstance(self.end, datetime.date) else self.end.date()).strftime('%Y-%m-%d'),
        }


class AllDayEventsManager(models.Manager):
    def eventsInRange(self, start: datetime.date, end: datetime.date):
        """
            Return all TimeRange objects that overlap with the
            start and end date
        """
        query = super().get_queryset().filter(
            day__lte=end,
            day__gte=start)

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


class OrgUnitDelegateManager(models.Manager):
    def isDelegateForUser(self, request, otheruser):
        if otheruser is None or request.user is None:
            return False
        if otheruser.id == request.user.id:
            return True
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList(
            request.user.id)
        teammember = TeamMember.objects.get(pk=otheruser.id)
        if teammember.orgunit_id in delegatedOUList:
            return True
        return False

    def delegatedOUIdList(self, user_id):
        delegatedOUList = list(super().filter(
            user__id=user_id).values_list('orgunit_id', flat=True))
        delegatedOUListRecursive = list(
            map(lambda ou: ou.id, OrgUnit.objects.queryDescendants(delegatedOUList)))
        return delegatedOUListRecursive

    def delegatedUsers(self, user_id):
        delegatedOUList = self.delegatedOUIdList(user_id)

        people = list(TeamMember.objects.filter(
            orgunit__id__in=delegatedOUList))

        return people


class OrgUnitDelegate(models.Model):
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE,
                                verbose_name=pgettext_lazy('Delegate', 'Organizational unit'))
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name=pgettext_lazy('Delegate', 'User'))
    objects = OrgUnitDelegateManager()

    def __str__(self):
        return str(format_lazy(
            pgettext_lazy(
                'Models', 'Delegation for {orgunit}'
            ), orgunit=self.orgunit))

    class Meta:
        verbose_name = pgettext_lazy(
            'Models', 'Delegate for an organizational unit')
        verbose_name_plural = pgettext_lazy(
            'Models', 'Delegate for organizational units')
        permissions = [
            ("assign_delegates", "Can assign delegates")
        ]


def query_events_timeranges(
        start: datetime.date,
        end: datetime.date,
        orgunits: List[OrgUnit] = None,
        users: List[str] = None
):
    alldayevents = AllDayEvent.objects.eventsInRange(start, end)
    timeranges = TimeRange.objects.eventsInRange(
        start, end, orgunits=orgunits, users=users)
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


def query_events_list1(start, end, orgunit=None):
    if start is None:
        start = datetime.date.today()
    if end is None or end < start:
        end = start + datetime.timedelta(days=100)
    orgunits = OrgUnit.objects.listDescendants(
        orgunit) if orgunit is not None else None
    return (query_events_timeranges(start, end, orgunits), start, end)


def collect_descendents(org_units: List[OrgUnit], parent_id: int):
    collected_ids = []
    ids_to_check = [parent_id]
    while True:
        pid = ids_to_check.pop(0)
        for org_unit in org_units:
            if org_unit.parent_id == pid:
                collected_ids.append(org_unit.id)
                ids_to_check.append(org_unit.id)
        if len(ids_to_check) == 0:
            break
    return collected_ids


def get_children(org_units: List[OrgUnit]):
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


def user_display_name(user):
    full_name = user.get_full_name()
    return full_name if full_name != "" else user.username
