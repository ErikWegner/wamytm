import datetime
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Greatest, Least
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from typing import List


class OrgUnitManager(models.Manager):
    def selectListItems(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        return toplevel

    def selectListItemsWithAllChoice(self):
        all_org_units = super().all()
        toplevel = get_children(all_org_units)
        toplevel.insert(0, ("", "All"))
        return toplevel

    def listDescendants(self, parent_id):
        all_org_units = super().all()
        descendants = collect_descendents(all_org_units, parent_id)
        descendants.insert(0, parent_id)
        return descendants


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


@receiver(post_save, sender=User)
def create_teammember(sender, instance, created, **kwargs):
    if created:
        TeamMember.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_teammember(sender, instance, **kwargs):
    instance.teammember.save()


class TimeRangeManager(models.Manager):
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

    def eventsInRange(self, start: datetime.date, end: datetime.date, orgunits: List[OrgUnit] = None):
        """
            Return all TimeRange objects that overlap with the
            start and end date
        """
        query = super().get_queryset().filter(
            start__lte=end,
            end__gte=start).annotate(
                start_trim=Greatest('start', start),
                end_trim=Least('end', end)
        )

        if orgunits is not None:
            query = query.filter(orgunit__in=orgunits)

        return query


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

    def clean(self):
        print('clean')
        if self.end is not None and self.end < self.start:
            raise ValidationError(
                {'end': _('End date may not be before start date.')})

    def save(self, *args, **kwargs):
        if self.end == None:
            self.end = self.start
        super().save(*args, **kwargs)

    def getDayCount(self):
        return (self.end - self.start).days

    def __str__(self):
        return f"TimeRange({self.start}, {self.end})"

def collect_descendents(org_units: List[OrgUnit], parent_id: int):
    collected_ids = []
    ids_to_check = [parent_id]
    while True:
        pid = ids_to_check.pop(0)
        for org_unit in org_units:
            if org_unit.parent_id == pid:
                collected_ids.append(org_unit.id)
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
