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
