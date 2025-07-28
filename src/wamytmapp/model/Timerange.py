from django.core.exceptions import ValidationError
from django.utils.text import format_lazy
from simple_history.models import HistoricalRecords
import json
from .base import *
from .OrgUnit import OrgUnit
from .ODB import ODB_ORG, OMS
from django.db.models.functions import Greatest, Least

class SafeJSONField(models.JSONField):
    """
    A JSONField that handles cases where the database returns 
    already-deserialized data instead of JSON strings
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        
        # Handle Oracle LOB objects - check for various Oracle LOB types
        if hasattr(value, '_impl') or hasattr(value, 'read'):
            # This is a proper LOB object, read its value
            try:
                lob_value = value.read()
                if isinstance(lob_value, bytes):
                    lob_value = lob_value.decode('utf-8')
                return json.loads(lob_value, cls=self.decoder) if lob_value else {}
            except Exception:
                return {}
        
        # Handle Oracle-specific issue where LOB is returned as dict without _impl
        if isinstance(value, dict):
            # Check if this is a problematic Oracle LOB dict
            if not hasattr(value, '_impl') and len(value) == 0:
                # Empty Oracle LOB dict, return empty dict
                return {}
            # Check if it has Oracle-specific internal structure that shouldn't be exposed
            oracle_internal_keys = ['_connection', '_cursor', '_locator', '_lobtype']
            if any(key in value for key in oracle_internal_keys):
                # This is an Oracle internal dict, return empty dict to avoid errors
                return {}
            try:
                # If it's already a proper dict structure, return it
                if all(isinstance(k, (str, int, float, bool, type(None))) for k in value.keys()):
                    return value
                # Otherwise return empty dict
                return {}
            except Exception:
                return {}
        
        # If the value is already a list, return it as-is
        if isinstance(value, list):
            return value
            
        # If it's a string, try to parse it as JSON
        if isinstance(value, str):
            try:
                return json.loads(value, cls=self.decoder)
            except (json.JSONDecodeError, TypeError):
                # If parsing fails, return empty dict
                return {}
        
        # For any other type, return empty dict to avoid errors
        return {}

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
            if item.von >= start and item.bis <= end:
                mod['res'] = TimeRangeManager.OVERLAP_DELETE
            elif item.von < start and item.bis > end:
                mod['res'] = TimeRangeManager.OVERLAP_SPLIT
            elif item.von < start:
                mod['res'] = TimeRangeManager.OVERLAP_NEW_END
            elif item.bis > end:
                mod['res'] = TimeRangeManager.OVERLAP_NEW_START
            
            # Vormittag/Nachmittag 
            item_data = item.safe_data()
            if item_data and 'partial' in item_data and part:
                if item_data['partial'] != part and kind != item.kind:
                    continue

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
    orgunit = models.ForeignKey(OrgUnit,blank=True, null=True,on_delete=models.CASCADE,verbose_name=pgettext_lazy('TimeRange', 'Organizational unit'))
    von = models.DateField(verbose_name=pgettext_lazy('TimeRange', 'Start'))
    bis = models.DateField(blank=True, verbose_name=pgettext_lazy('TimeRange', 'End'))
    kind = models.CharField(choices=KIND_CHOICES, max_length=1, default=ABSENT, verbose_name=pgettext_lazy('TimeRange', 'Kind of time range'))
    data = SafeJSONField(encoder=DjangoJSONEncoder)

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

    def save(self, *args, **kwargs):
        if self.bis == None:
            self.bis = self.von
        super().save(*args, **kwargs)

    def safe_data(self):
        """
        Safely access the data field, handling cases where it might be deferred
        or cause Oracle LOB issues
        """
        try:
            # Try to access the data field
            if hasattr(self, '_state') and self._state.fields_cache and 'data' not in self._state.fields_cache:
                # Field is deferred, return empty dict
                return {}
            return self.data if self.data is not None else {}
        except Exception:
            # If there's any error accessing the data field, return empty dict
            return {}

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
            'desc': data.get('desc', '') if data else "", # wird nicht verwendet!
            'partial': [ x for x in partial if x[0] == data['partial']][0][1] if data and 'partial' in data else "", # wird nicht verwendet!
        }