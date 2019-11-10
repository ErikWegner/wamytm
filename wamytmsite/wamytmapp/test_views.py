import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from .models import TimeRange, OrgUnit
from .views import _prepareWeekdata


class ViewsTests(TestCase):
    def setUp(self):
        self.users = []
        for userindex in range(0, 5):
            self.users.append(User.objects.create_user(
                F'unittestuser{userindex}'))
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        wednesday = monday + datetime.timedelta(days=2)
        friday_before = monday - datetime.timedelta(days=3)
        tuesday_after = monday + datetime.timedelta(days=8)

        # An object inside the boundaries
        self.inside = self.hasTimeRangeObject(
            wednesday, wednesday, self.users[4])
        # An object overlapping to the left
        self.leftOverlap = self.hasTimeRangeObject(
            friday_before, monday, self.users[2])
        # An object overlapping to the right
        self.rightOverlap = self.hasTimeRangeObject(
            wednesday, tuesday_after, self.users[1])
        # An object totally outside the boundaries (earlier)
        self.outsideLeft = self.hasTimeRangeObject(
            monday - datetime.timedelta(days=5), monday - datetime.timedelta(days=4), self.users[3])
        # An object totally outside the boundaries (later)
        self.outsideRight = self.hasTimeRangeObject(
            monday + datetime.timedelta(days=9), monday + datetime.timedelta(days=12), self.users[0])

    def test_prepareWeekData(self):
        # Act
        queryResult = TimeRange.objects.thisWeek()
        result = _prepareWeekdata(queryResult)

        # Assert
        self.assertSequenceEqual(
            result, [
                {'days': [0, 0, 'a', 0, 0], 'user': self.users[4]},
                {'days': ['a', 0, 0, 0, 0], 'user': self.users[2]},
                {'days': [0, 0, 'a', 'a', 'a'], 'user': self.users[1]}
            ])

    def hasTimeRangeObject(self, start: datetime.date, end: datetime.date, user: User):
        timeRange = TimeRange(start=start, end=end,
                              user=user, orgunit=self.org_unit, kind=TimeRange.ABSENT)
        timeRange.save()
        return timeRange

    def d(self, s: str):
        return datetime.datetime.strptime(s, "%Y-%m-%d")
