import datetime
from random import choice, randint
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from wamytmapp.models import OrgUnit, TeamMember, TimeRange, AllDayEvent


class Command(BaseCommand):
    help = 'Generate example organizational units, users and time entries'
    requires_migrations_checks = True
    last_names = ['Turner', 'Cook', 'Wood', 'Smith', 'Jones',
                  'Miller', 'Taylor', 'Anderson', 'Wright', 'Baker']
    first_names = ['Mary', 'James', 'Linda', 'Michael',
                   'Karen', 'Daniel', 'Sandra', 'Christopher']

    def generateOrgUnits(self):
        o = OrgUnit(name='Korporator HQ')
        o.save()

        rd = OrgUnit(name='Research&Development', parent=o)
        rd.save()

        hr = OrgUnit(name='Recruting', parent=o)
        hr.save()

        t = OrgUnit(name='Trainees', parent=hr)
        t.save()

        self._orgunits = [o, rd, hr, t]

    def generateUsers(self, count):
        self._teammembers = []
        for user_index in range(count):
            user = User.objects.create_user(
                F'user{user_index}',
                first_name=choice(Command.first_names),
                last_name=choice(Command.last_names))
            user.save()
            tm = TeamMember(
                user=user,
                orgunit=choice(self._orgunits)
            )
            tm.save()
            self._teammembers.append(tm)

    def generateTimeRanges(self, count):
        today = datetime.date.today()
        mondayLastWeek = today - \
            datetime.timedelta(days=today.weekday() + 7)
        for _ in range(count):
            start = mondayLastWeek + datetime.timedelta(days=randint(0, 100))
            end = start + \
                datetime.timedelta(days=choice(
                    [1, 1, 1, 1, 1, 3, 5, 7, 14, 21]))
            tm = choice(self._teammembers)
            tr = TimeRange(
                user=tm.user,
                orgunit=tm.orgunit,
                start=start,
                end=end,
                kind=choice(TimeRange.KIND_CHOICES)[0],
                data={'v': 1}
            )
            if tr.kind == TimeRange.MOBILE and randint(0, 10) % 4 == 0:
                tr.data[TimeRange.DATA_KINDDETAIL] = 'p'
            if randint(0, 10) < 3:
                tr.data[TimeRange.DATA_PARTIAL] = 'f' if randint(0,2) % 2 == 0 else 'a'

            # Create some old entries without data
            if randint(0, 20) < 1:
                tr.data = {}
            tr.save()

    def generateAllDayEvents(self):
        today = datetime.date.today()
        mondayLastWeek = today - \
            datetime.timedelta(days=today.weekday() + 7)
        for _ in range(25):
            day = mondayLastWeek + datetime.timedelta(days=randint(0, 100))
            AllDayEvent(
                description='A special day',
                day=day
            ).save()

    def removeData(self):
        AllDayEvent.objects.all().delete()
        TimeRange.objects.all().delete()
        TeamMember.objects.all().delete()
        User.objects.filter(is_staff=False).delete()
        OrgUnit.objects.all().delete()

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Deleting data'))
        self.removeData()
        self.stdout.write(self.style.NOTICE('Generating data'))
        self.generateOrgUnits()
        self.generateUsers(25)
        self.stdout.write(self.style.NOTICE('Generating time entries'))
        self.generateTimeRanges(60)
        self.generateAllDayEvents()
        self.stdout.write(self.style.SUCCESS(
            'Successfully generated data'))
