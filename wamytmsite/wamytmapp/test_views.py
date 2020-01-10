import datetime
from django.test import TestCase
from django.contrib.auth.models import User
from .models import TimeRange, OrgUnit, AllDayEvent, query_events_timeranges_in_week, user_display_name
from .views import _prepareWeekdata, _prepareList1Data


class ViewsTests(TestCase):
    def setUp(self):
        self.users = []
        for userindex in range(0, 5):
            self.users.append(User.objects.create_user(
                F'unittestuser{userindex}'))
        self.org_unit = OrgUnit(name='unittestou')
        self.org_unit.save()

    def test_prepareList1Data(self):
        # Arrange
        for user in self.users:
            user.display_name = user_display_name(user)
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        next_monday = monday + datetime.timedelta(days=7)
        friday_2weeks = next_monday + datetime.timedelta(days=(4+7))

        self.hasTimeRangeObject(next_monday, friday_2weeks, self.users[4])

        range_start = monday
        range_end = range_start + datetime.timedelta(days=27)

        # Act
        queryResult = TimeRange.objects.eventsInRange(range_start, range_end)
        result = _prepareList1Data(queryResult, range_start, range_end)

        # Assert
        self.assertEqual(range_start.weekday(), 0, "Starts on Monday")
        self.assertEqual(range_end.weekday(), 6, "Ends on Sunday")
        self.assertEqual(len(result['lines']), 20,
                         "output is 4 weeks with 5 days a week")
        for i, line in enumerate(result['lines']):
            line_date = line['day']
            self.assertEqual(line['start_of_week'], line_date.day.weekday(
            ) == 0, F"start_of_week failed on ${line_date}")
            if i <= 4:
                self.assertEqual(
                    result['lines'][i]['cols'], [[]], F"Any day in the first week has no item, but day {line_date} ({i}) has")
            elif i <= 14:
                self.assertNotEqual(
                    result['lines'][i]['cols'], [[]], F"Any day in the 2nd and 3rd week has an item, but day {line_date} ({i}) has none")
            else:
                self.assertEqual(
                    result['lines'][i]['cols'], [[]], F"Any day in the last week has no item, but day {line_date} ({i}) has")

    def test_prepareWeekData(self):
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
        # An all day event on tuesday
        self.hasAllDayEvent(description = "ruby tue", day = monday + datetime.timedelta(days=1))
        # An all day event on friday
        self.hasAllDayEvent(description = "frik", day = monday + datetime.timedelta(days=4))

        # Act
        queryResult, allDayEventsResult = query_events_timeranges_in_week()
        result = _prepareWeekdata(queryResult)

        # Assert
        self.assertSequenceEqual(
            result, [
                {'days': [0, 0, 'a', 0, 0], 'user': self.users[4], 'username': user_display_name(self.users[4])},
                {'days': ['a', 0, 0, 0, 0], 'user': self.users[2], 'username': user_display_name(self.users[2])},
                {'days': [0, 0, 'a', 'a', 'a'], 'user': self.users[1], 'username': user_display_name(self.users[1])}
            ])
        self.assertEqual(allDayEventsResult[0].description, "ruby tue")
        self.assertEqual(allDayEventsResult[1].description, "frik")

    def hasTimeRangeObject(self, start: datetime.date, end: datetime.date, user: User):
        timeRange = TimeRange(start=start, end=end,
                              user=user, orgunit=self.org_unit, kind=TimeRange.ABSENT)
        timeRange.save()
        return timeRange

    def hasAllDayEvent(self, day: datetime.date, description: str):
        allDayEvent = AllDayEvent(description=description, day=day)
        allDayEvent.save()

    def d(self, s: str):
        return datetime.datetime.strptime(s, "%Y-%m-%d")
