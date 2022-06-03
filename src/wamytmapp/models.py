import datetime

from django.contrib.auth.models import User, AbstractUser
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models, connection
from django.db.models.functions import Greatest, Least
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.text import format_lazy
from django.utils.translation import pgettext_lazy
from django_prometheus.models import ExportModelOperationsMixin
from simple_history.models import HistoricalRecords
from typing import List


#class User(AbstractUser):
#    pass

class OMSManager(models.Manager):
    def getMIT_ID(self, user_id):
        return super().all().filter(user_id__exact=user_id)[0]

    def getORG_ID(self,user_id):
        qu = super().raw('''
select * from v_getORGID t where t.user_id = %s
        ''', params=[user_id])

        if len(qu) == 0:
            return None

        return qu[0]
    def queryAllTeammember(self, parents):
        parentslist = tuple(parents if type(parents) is list else [parents])
        if len(parentslist) == 0:
            return list()
        qu = super().raw('''
        SELECT u.id
        FROM odb_mitarbeiter2strukt t
        JOIN wamytmapp_oms g ON g.mit_id = t.m2o_mit_id
        JOIN auth_user u on u.id = g.user_id
        where CURRENT_DATE >= COALESCE(t.m2o_von, '1970-01-01':: date)
          AND CURRENT_DATE <= COALESCE(t.m2o_bis, '2099-12-31':: date)
          and t.m2o_org_id in %s
        ''', params=[parentslist])
        return list(qu)

    def queryTeammember(self, parents):
        parentslist = tuple(parents if type(parents) is list else [parents])
        if len(parentslist) == 0:
            return list()
        qu = super().raw('''
        SELECT t.*, u.first_name, u.last_name, g.org_name, g.org_kbez
        FROM v_getorgid t
        JOIN odb_org g
        ON g.org_id = t.m2o_org_id
        JOIN auth_user u
        on u.id = t.user_id
        where t.m2o_org_id in %s
        ''', params=[parentslist])
        return list(qu)


class OMS(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mit_id = models.IntegerField(null=True)
    objects = OMSManager()

class ODB_STRUKT_Manager(models.Manager):
    def SelectList_with_Orgs(self):
        all_org_units = super().all().values_list("m_id", "m_org_id")
        return all_org_units

class ODB_STRUKT(models.Model):
    m_id = models.IntegerField(primary_key=True)
    m_parent_id = models.IntegerField(null=True)
    m_org_id = models.IntegerField(null=True)
    m_von = models.DateField(blank=True, null=True)
    m_bis = models.DateField(blank=True, null=True)
    objects = ODB_STRUKT_Manager()
    class Meta:
        #managed = False
        db_table = 'odb_strukt'

class orgs4wamytm(models.Model):
    ko_m = models.OneToOneField(ODB_STRUKT, on_delete=models.PROTECT, primary_key=True)

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

    def queryDescendants2(self, parents):
        parentslist = tuple(parents if type(parents) is list else [parents])
        if len(parentslist) == 0:
            return list()
        qu = super().raw('''
        WITH RECURSIVE ou AS (
            SELECT t.id, t.parent_id
            FROM mv_odb_org t
            WHERE t.id in %s
        UNION ALL
            SELECT t2.id, t2.parent_id
            FROM mv_odb_org t2
            JOIN ou t1
            ON t2.parent_id = t1.id
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
        
        
        
def dictfetchall(cursor):
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]
      
def my_custom_sql(orgid, day_of_week, users):
    if users is not None and len(users) > 0:
        user =  "and u.username in (" + ','.join(map(lambda x: "'" + x + "'", users)) + ")"
    else:
        user = ''

    with connection.cursor() as cursor:
        cursor.execute("""
with recursive config as (
  select
    von,
    von + 4 as bis,
    org_id
  from
    (
      select
        %s::date as von,
        %s::INTEGER as org_id
    ) t
),
wt as (
  select
    t.von as level,
    t.bis
  from
    config t
  union
  select
    level + 1,
    bis
  from
    wt
  where
    level < bis
),
src as (
  select distinct 
    t.*,
    u.last_name || ', ' || u.first_name || ' (' || upper(substr(u.username, 2)) || ')' as user_name
  from
    wamytmapp_timerange t
    cross join config g
    left join auth_user u on u.id = t.user_id

    left join wamytmapp_oms oms on oms.user_id = t.user_id
    left join odb_mitarbeiter2strukt m2o on m2o.m2o_mit_id = oms.mit_id and CURRENT_DATE >= COALESCE(m2o.m2o_von, '1970-01-01':: date) AND CURRENT_DATE <= COALESCE(m2o.m2o_bis, '2099-12-31':: date)

  where 1=1
    
    and coalesce(m2o.m2o_org_id, -1) = coalesce(g.org_id, m2o.m2o_org_id, -1)
    and t.start <= g.bis
    and t.end >= g.von
    """ + user + """
),
ce as (
  select
    distinct wt.level,
    src.user_name
  from
    src
    cross join wt
),
asd as (
  select
    t.*,
    case
      when coalesce(t.lag, 'yaa') != coalesce(t.kind, 'yaa')
      or coalesce(t.lag_desc, 'yaa') != coalesce(t.desc, 'yaa')
      or coalesce(t.lag_partial, 'yaa') != coalesce(t.partial, 'yaa') then 1
    end as ca
  from
    (
      select
        t.*,
        lag(t.kind, 1, 'easd') over(
          partition by t.user_name
          order by
            t.level
        ) as lag,
        lag(t.desc, 1, 'easd') over(
          partition by t.user_name
          order by
            t.level
        ) as lag_desc,
        lag(t.partial, 1, 'easd') over(
          partition by t.user_name
          order by
            t.level
        ) as lag_partial
      from
        (
          select
            t.level,
            t.user_name,
            t.data,
            min(t.wertung) as wertung,
            STRING_AGG(t.desc,'; ' order by t.partial desc) as desc,
            DENSE_RANK() OVER(
              partition by t.level,
              t.user_name
              order by
                min(t.wertung) desc,
                min(t.desc) nulls last
            ) as rn,
            case
              when t.cnt = 1 then coalesce('-' || min(t.partial), '')
            end as partial,
            case
              when t.cnt = 2 then STRING_AGG(
                t.kind,
                ''
                order by
                  t.partial desc
              )
              else (
                array_agg(
                  t.kind
                  order by
                    t.wertung desc
                )
              ) [ 1 ]
            end as kind
          from
            (
              select
                t.level,
                t.user_name,
                g.kind,
                g.data - 'partial' - 'desc' as data,
                g.data ->> 'partial' as partial,
                g.data ->> 'desc' as desc,
                count(g.data ->> 'partial') over(partition by t.level, t.user_name) as cnt,
                o.wertung
              from
                ce t
                left join src g on t.user_name = g.user_name
                and t.level between g.start
                and g.
            end
            left join wamytmapp_kind o on o.kind = g.kind
        ) t
      group by
        t.level,
        t.user_name,
        t.data,
        t.cnt
    ) t
  where
    t.rn = 1
) t
),
baum as (
  select
    t.*,
    1 as lvl,
    to_char(t.level, 'DDD'):: INTEGER as root
  from
    asd t
  where
    ca = 1
  union
  select
    t.*,
    lvl + 1,
    g.root
  from
    asd t
    join baum g on t.user_name = g.user_name
    and coalesce(t.data, '{}':: jsonb) = coalesce(g.data, '{}':: jsonb)
    and t.level = g.level + 1
    and coalesce(t.desc, 'y') = coalesce(g.desc, 'y')
    and coalesce(t.kind, 'y') = coalesce(g.kind, 'y')
    and coalesce(t.partial, 'y') = coalesce(g.partial, 'y')
)
select
  t.user_name,
  t.kind,
  t.data ->> 'v' as data_v,
  t.desc,
  coalesce(t.partial,'') as partial,
  min(t.level),
  max(t.lvl) as span,
  dense_rank() over(
    partition by t.user_name
    order by
      min(t.level)
  ) as dn
from
  baum t
group by
  t.root,
  t.user_name,
  t.kind,
  t.partial,
  t.desc,
  t.data
order by
  t.user_name,
  min(t.level)
 """, (day_of_week,orgid))
        row = dictfetchall(cursor)
	
    return row


class odb_org_Manager(models.Manager):		
	def selectListItemsWithAllChoice(self):
	        all_org_units = super().all()
	        toplevel = get_children(all_org_units)
	        toplevel.insert(0, ("", pgettext_lazy('OrgUnitManager', "All")))
	        return toplevel

class mv_odb_org(models.Model):
	id = models.BigIntegerField(primary_key=True)
	name = models.CharField(max_length=255)
	parent = models.ForeignKey('self', on_delete=models.DO_NOTHING, blank=True, null=True)
	objects = odb_org_Manager()
	class Meta:
		managed = False
		db_table = 'mv_odb_org'

class MV_OMS_DATEN(models.Model):
    mit_id = models.BigIntegerField(primary_key=True)
    mit_name_akt = models.CharField(max_length=255, null=True)
    mit_vorname = models.CharField(max_length=255, null=True)
    mit_austritt = models.DateField(blank=True, null=True)
    kid = models.CharField(max_length=255, null=True)
    class Meta:
        #managed = False
        db_table = 'mv_oms_daten'

class ODB_ORG(models.Model):
    org_id = models.IntegerField(primary_key=True)
    org_name = models.CharField(max_length=255, null=True)
    org_kbez = models.CharField(max_length=255, null=True)
    class Meta:
        db_table = 'odb_org'

    def __str__(self):
        return self.org_name + " (" + self.org_kbez + ")"

class ODB_MITARBEITER2STRUKT(models.Model):
    m2o_id = models.IntegerField(primary_key=True)
    m2o_mit_id = models.BigIntegerField(null=True)
    m2o_org_id = models.IntegerField(null=True)
    m2o_von = models.DateField(blank=True, null=True)
    m2o_bis = models.DateField(blank=True, null=True)
    m2o_typ = models.IntegerField(blank=True, null=True)
    class Meta:
        #managed = False
        db_table = 'odb_mitarbeiter2strukt'
	
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
            query = query.filter(user__in=list(map(lambda x: x.id,OMS.objects.queryAllTeammember(orgunits)))) 
            #query = query.filter(org_id__in=orgunits)

        if userid is not None:
            query = query.filter(user__id=userid)

        if users is not None and len(users) > 0:
            users_qs = User.objects.filter(username__in=users)
            query = query.filter(user__in=users_qs)

        return query

    def overlapResolution(self, start: datetime.date, end: datetime.date, userid: int, kind: str, part: str):
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
            
            # Vormittag/Nachmittag 
            if 'partial' in item.data and part:
                if item.data['partial'] != part and kind != item.kind:
                    continue

            r['mods'].append(mod)

        return r


class TimeRange(ExportModelOperationsMixin('timerange'), models.Model):
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=pgettext_lazy('TimeRange', 'User'))
    orgunit = models.ForeignKey(OrgUnit,blank=True, null=True,on_delete=models.CASCADE,verbose_name=pgettext_lazy('TimeRange', 'Organizational unit'))
    start = models.DateField(verbose_name=pgettext_lazy('TimeRange', 'Start'))
    end = models.DateField(
        blank=True, verbose_name=pgettext_lazy('TimeRange', 'End'))
    kind = models.CharField(choices=KIND_CHOICES, max_length=1, default=ABSENT,
                            verbose_name=pgettext_lazy('TimeRange', 'Kind of time range'))
    data = models.JSONField(encoder=DjangoJSONEncoder)

    org = models.ForeignKey(ODB_ORG, blank=True, null=True,on_delete=models.SET_NULL,verbose_name=pgettext_lazy('TimeRange', 'Organizational unit'))
    #org_id =  models.IntegerField(blank=True, null=True)

    history = HistoricalRecords()

    objects = TimeRangeManager()

    class Meta:
        verbose_name = pgettext_lazy('Models', 'time range')
        verbose_name_plural = pgettext_lazy('Models', 'time ranges')
        indexes = [
            models.Index(fields=['start', 'end']),
            models.Index(fields=['org_id', 'start', 'end']),
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
        #return str(format_lazy('{s}({start}, {end})', s=s, start=self.start, end=self.end))
        return str(format_lazy('{s}({team}|{user}: {start}, {end})', s=s, team=self.org_id, user=self.user_id, start=self.start, end=self.end))
        
    def new_kind(self):
        r = self.kind
        if self.data and TimeRange.DATA_PARTIAL in self.data and len(self.kind) == 1:
            r = r + '-' + self.data[TimeRange.DATA_PARTIAL]
        if self.data and TimeRange.DATA_KINDDETAIL in self.data:
            r = r + self.data[TimeRange.DATA_KINDDETAIL]
        return r

    def kind_with_details(self):
        r = self.kind
        if self.data and TimeRange.DATA_KINDDETAIL in self.data:
            r = r + self.data[TimeRange.DATA_KINDDETAIL]
        return r

    def buildConflictJsonStructure(self):
        partial = [('a','Nachmittag'),('f','Vormittag')]

        return {
            'id': self.id,
            'start': (self.start if isinstance(self.start, datetime.date) else self.start.date()).strftime('%Y-%m-%d'),
            'end': (self.end if isinstance(self.end, datetime.date) else self.end.date()).strftime('%Y-%m-%d'),
            'kind': [ x for x in self.KIND_CHOICES if x[0] == self.kind][0][1],
            'desc': self.data['desc'] if 'desc' in self.data  else "",
            'partial': [ x for x in partial if x[0] == self.data['partial']][0][1] if 'partial' in self.data  else "",
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

class KIND(models.Model):
    kind = models.CharField(choices=TimeRange.KIND_CHOICES, max_length=1,primary_key=True)
    wertung = models.SmallIntegerField(blank=True, null=True)

class OrgUnitDelegateManager(models.Manager):
    def isDelegateForUser(self, request, otheruser):
        if otheruser is None or request.user is None:
            return False
        if otheruser.id == request.user.id:
            return True
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList2(
            request.user.id)
        #teammember = TeamMember.objects.get(pk=otheruser.id)
        teammember = OMS.objects.getORG_ID(otheruser.id).m2o_org_id
        #if teammember.orgunit_id in delegatedOUList:
        if teammember in delegatedOUList:
            return True
        return False

    def delegatedOUIdList(self, user_id):
        delegatedOUList = list(super().filter(user__id=user_id).values_list('orgunit_id', flat=True))
        delegatedOUListRecursive = list(map(lambda ou: ou.id, OrgUnit.objects.queryDescendants(delegatedOUList)))
        return delegatedOUListRecursive

    def delegatedUsers(self, user_id):
        delegatedOUList = self.delegatedOUIdList(user_id)

        people = list(TeamMember.objects.filter(
            orgunit__id__in=delegatedOUList))

        return people

    def delegatedOUIdList2(self, user_id):
        delegatedOUList = list(super().filter(user__id=user_id).values_list('org_id', flat=True))
        delegatedOUListRecursive = list(map(lambda ou: ou.id, OrgUnit.objects.queryDescendants2(delegatedOUList)))
        return delegatedOUListRecursive

    def delegatedUsers2(self, user_id):
        delegatedOUList = self.delegatedOUIdList2(user_id)

        #people = list(TeamMember.objects.filter(orgunit__id__in=delegatedOUList))
        people = list(map(lambda ou: (ou.user_id, ou.first_name, ou.last_name,ou.org_name, ou.org_kbez), OMS.objects.queryTeammember(delegatedOUList)))
        return people


class OrgUnitDelegate(models.Model):
    orgunit = models.ForeignKey(OrgUnit, blank=True, null=True,on_delete=models.SET_NULL,
                                verbose_name=pgettext_lazy('Delegate', 'Organizational unit'))
    user = models.ForeignKey(User, on_delete=models.CASCADE,
                             verbose_name=pgettext_lazy('Delegate', 'User'))
    org = models.ForeignKey(ODB_ORG, blank=True, null=True,on_delete=models.SET_NULL)
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

    ret = (query_events_timeranges(start, end, orgunits), start, end)
    
    return ret


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
    #full_name = user.get_full_name()
    full_name = user.last_name + ", " + user.first_name
    return full_name if full_name != "" else user.username
