import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from .models import TimeRange, OrgUnit


class TimeRangeManagerTestQueries(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('unittestuser1')
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

        # An object inside the boundaries
        self.inside = self.hasTimeRangeObject('2019-11-05', '2019-11-05')
        # An object overlapping to the left
        self.leftOverlap = self.hasTimeRangeObject('2019-11-01', '2019-11-04')
        # An object overlapping to the right
        self.rightOverlap = self.hasTimeRangeObject('2019-11-09', '2019-11-15')
        # An object totally outside the boundaries (earlier)
        self.outsideLeft = self.hasTimeRangeObject('2019-11-01', '2019-11-01')
        # An object totally outside the boundaries (later)
        self.outsideRight = self.hasTimeRangeObject('2019-11-11', '2019-11-11')

        # Monday (left boundary)
        self.queryStart = self.d('2019-11-04')
        # Sunday (right boundary)
        self.queryEnd = self.d('2019-11-10')

        # Filter events
        self.result = TimeRange.objects.eventsInRange(
            self.queryStart, self.queryEnd)

    def test_expectedNumOfDates(self):
        self.assertEqual(len(self.result), 3)

    def test_dateWithinRange(self):
        self.assertTrue(self.inside in self.result)

    def test_dateOverlapLeft(self):
        self.assertTrue(self.leftOverlap in self.result)

    def test_dateOverlapRight(self):
        self.assertTrue(self.rightOverlap in self.result)

    def hasTimeRangeObject(self, start: str, end: str):
        startDate = self.d(start)
        endDate = self.d(end)
        timeRange = TimeRange(start=startDate, end=endDate, user=self.user,
                              orgunit=self.org_unit, kind=TimeRange.ABSENT, data={})
        timeRange.save()
        return timeRange

    def d(self, s: str):
        return datetime.datetime.strptime(s, "%Y-%m-%d")
