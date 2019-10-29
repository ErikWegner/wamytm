import datetime
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class OrgUnit(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return f"{self.user} ({self.orgunit})"


class TimeRangeManager(models.Manager):
    def thisWeek(self):
        """
            Return all TimeRange objects that start during this week or
            that end during this week.
        """
        today = datetime.date.today()
        monday = today - datetime.timedelta(days=today.weekday())
        friday = monday + datetime.timedelta(days=5)
        return self.eventsInRange(monday, friday)


    def eventsInRange(self, start: datetime.date, end: datetime.date):
        """
            Return all TimeRange objects that overlap with the
            start and end date
        """
        return super().get_queryset().filter(
            start__gte=start,
            start__lte=end,
            end__gte=start,
            end__lte=end)


class TimeRange(models.Model):
    ABSENT = 'a'
    PRESENT = 'p'
    KIND_CHOICES = [
        (ABSENT, 'absent'),
        (PRESENT, 'present'),
    ]
    user = models.OneToOneField(TeamMember, on_delete=models.CASCADE)
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.CASCADE)
    start = models.DateField()
    end = models.DateField(blank=True)
    kind = models.CharField(choices=KIND_CHOICES, max_length=1, default=ABSENT)

    objects = TimeRangeManager()

    def save(self, *args, **kwargs):
        if self.end == None:
            self.end = self.start
        super().save(*args, **kwargs)

    def getDayCount(self):
        return (self.end - self.start).days

    def __str__(self):
        return f"TimeRange({self.start}, {self.end})"