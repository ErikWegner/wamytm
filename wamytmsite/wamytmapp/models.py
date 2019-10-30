import datetime
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from typing import List


class OrgUnitManager(models.Manager):
    def selectListItems(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units, 0)
        return toplevel


class OrgUnit(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True)

    objects = OrgUnitManager()

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True,)
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
    MOBILE = 'm'
    KIND_CHOICES = [
        (ABSENT, 'absent'),
        (PRESENT, 'present'),
        (MOBILE, 'mobile'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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


def get_children(org_units: List[OrgUnit], parent_id=0, level=0):
    if level > 1:
        return []
    r = []
    for org_unit in org_units:
        if (parent_id == 0 and org_unit.parent is None and level == 0) or parent_id == org_unit.parent_id:
            children = get_children(
                org_units, parent_id=org_unit.id, level=level+1)
            # Does element has children?
            if len(children) > 0:
                children.insert(0, (org_unit.id, org_unit.name))
                r.append((org_unit.name, tuple(children)))
            else:
                r.append((org_unit.id, org_unit.name))
    return r
