from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from .model.sonst import TeamMember, AllDayEvent, query_events_timeranges_in_week, user_display_name
from .model.Timerange import TimeRange, TimeRangeManager
from .model.OrgUnit import OrgUnit, OrgUnitDelegate, collect_descendents, get_children

@receiver(post_save, sender=User)
def create_teammember(sender, instance, created, **kwargs):
    if created:
        TeamMember.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_teammember(sender, instance, **kwargs):
    if hasattr(instance, 'teammember'):
        instance.teammember.save()