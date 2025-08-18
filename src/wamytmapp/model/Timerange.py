from django.core.exceptions import ValidationError
from django.utils.text import format_lazy
from simple_history.models import HistoricalRecords
import json
from .base import *
from .OrgUnit import OrgUnit
from .ODB import ODB_ORG, OMS
from django.db.models.functions import Greatest, Least

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
            von__lte=end,
            bis__gte=start
        ).annotate(
            von_trim=Greatest(
                'von', start, output_field=models.DateField(default=datetime.datetime.now())),
            bis_trim=Least(
                'bis', end, output_field=models.DateField(default=datetime.datetime.now()))
        ).order_by(
            'user__last_name',
            'user__first_name',
            'user__username'
        )

        if orgunits is not None:
            query = query.filter(user__in=list(map(lambda x: x.id, OMS.objects.queryAllTeammember(orgunits)))) 
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
            
            if part is None or part == '':
                if item.von >= start and item.bis <= end:
                    mod['res'] = TimeRangeManager.OVERLAP_DELETE
                elif item.von < start and item.bis > end:
                    mod['res'] = TimeRangeManager.OVERLAP_SPLIT
                elif item.von < start:
                    mod['res'] = TimeRangeManager.OVERLAP_NEW_END
                elif item.bis > end:
                    mod['res'] = TimeRangeManager.OVERLAP_NEW_START
            else:
                # Vormittag/Nachmittag 
                item_data = item.safe_data()
                if item_data and 'partial' in item_data:
                    # partial Tag vorhanden
                    if item_data['partial'] == part:
                        # gleicher partial vorhanden (egal welcher Typ)
                        mod['res'] = TimeRangeManager.OVERLAP_DELETE
                    if item_data['partial'] != part:
                        # anderer partial vorhanden
                        continue
                else:
                    # vorhanden ganzen Tag aufsplitten
                    mod['res'] = TimeRangeManager.OVERLAP_SPLIT

            r['mods'].append(mod)

        return r
    
    
class TimeRange(ExportModelOperationsMixin('timerange'), models.Model):
    DATA_KINDDETAIL = 'kinddetail'
    DATA_DESCRIPTION = 'DATA_DESC'
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
    von = models.DateField(verbose_name=pgettext_lazy('TimeRange', 'Start'))
    bis = models.DateField(blank=True, verbose_name=pgettext_lazy('TimeRange', 'End'))
    kind = models.CharField(choices=KIND_CHOICES, max_length=1, default=ABSENT, verbose_name=pgettext_lazy('TimeRange', 'Kind of time range'))
    data = models.JSONField(encoder=DjangoJSONEncoder, null=True, blank=True, default=dict)

    org = models.ForeignKey(ODB_ORG, blank=True, null=True,on_delete=models.SET_NULL,verbose_name=pgettext_lazy('TimeRange', 'Organizational unit'))

    history = HistoricalRecords()

    objects = TimeRangeManager()

    class Meta:
        managed = False
        verbose_name = pgettext_lazy('Models', 'time range')
        verbose_name_plural = pgettext_lazy('Models', 'time ranges')
        indexes = [
            models.Index(fields=['von', 'bis']),
            models.Index(fields=['org_id', 'von', 'bis']),
        ]

    def clean(self):
        if self.bis is not None and self.bis < self.von:
            raise ValidationError(
                {'end': pgettext_lazy('Models', 'End date may not be before start date.')})
        
        # Validate that JSON data field doesn't exceed varchar2(4000) limit
        if self.data is not None:
            json_string = json.dumps(self.data, cls=DjangoJSONEncoder)
            if len(json_string) > 4000:
                raise ValidationError({
                    'data': pgettext_lazy('Models', 
                        'Data field is too long. Maximum allowed size is 4000 characters, current size is {} characters.').format(len(json_string))
                })

    def save(self, *args, **kwargs):
        if self.bis == None:
            self.bis = self.von
        
        # Additional safety check for data field size before saving
        if self.data is not None:
            json_string = json.dumps(self.data, cls=DjangoJSONEncoder)
            if len(json_string) > 4000:
                # Truncate or raise error - depending on your preference
                raise ValidationError(f'Data field exceeds 4000 character limit: {len(json_string)} characters')
        
        super().save(*args, **kwargs)

    def safe_data(self):
        return self.data if self.data is not None else {}

    def getDayCount(self):
        return (self.bis - self.von).days

    def __str__(self):
        s = pgettext_lazy('TimeRangeStr', "TimeRange")
        return str(format_lazy('{s}({team}|{user}: {start}, {end})', s=s, team=self.org_id, user=self.user_id, start=self.von, end=self.bis))
        
    def new_kind(self):
        r = self.kind
        data = self.safe_data()
        if data and TimeRange.DATA_PARTIAL in data and len(self.kind) == 1:
            r = r + '-' + data[TimeRange.DATA_PARTIAL]
        if data and TimeRange.DATA_KINDDETAIL in data:
            r = r + data[TimeRange.DATA_KINDDETAIL]
        return r

    def kind_with_details(self):
        r = self.kind
        data = self.safe_data()
        if data and TimeRange.DATA_KINDDETAIL in data:
            r = r + data[TimeRange.DATA_KINDDETAIL]
        return r

    def buildConflictJsonStructure(self):
        partial = [('a','Nachmittag'),('f','Vormittag')]
        data = self.safe_data()

        return {
            'id': self.id,
            'start': (self.von if isinstance(self.von, datetime.date) else self.von.date()).strftime('%Y-%m-%d'), # wird nicht verwendet!
            'end': (self.bis if isinstance(self.bis, datetime.date) else self.bis.date()).strftime('%Y-%m-%d'), # wird nicht verwendet!
            'kind': [ x for x in self.KIND_CHOICES if x[0] == self.kind][0][1], # wird nicht verwendet!
            'desc': data.get(self.DATA_DESCRIPTION, '') if data else "", # wird nicht verwendet!
            'partial': [ x for x in partial if x[0] == data['partial']][0][1] if data and 'partial' in data else "", # wird nicht verwendet!
        }