from django.test import TestCase
from django.contrib.auth.models import User

from ..models import TimeRange, OrgUnit
from .helpers import d, createAbsentTimeRangeObject


class TimeRangeModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('unittestuser1')
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

    def _hasTimeRangeObject(self, start: str, end: str):
        return createAbsentTimeRangeObject(start, end, self.user, self.org_unit)

    def test_buildConflictJsonStructure(self):
        o = self._hasTimeRangeObject('2020-03-31', '2020-04-05')

        d = o.buildConflictJsonStructure()

        self.assertEquals(d, {
            'id': o.id,
            'start': '2020-03-31',
            'end': '2020-04-05'
        })
