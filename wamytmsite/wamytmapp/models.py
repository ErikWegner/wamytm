from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# Create your models here.


class OrgUnit(models.Model):
    name = models.CharField(max_length=80)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, blank=True, null=True)

    def __str__(self):
        return self.name


class TeamMember(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.PROTECT)


# https://simpleisbetterthancomplex.com/tutorial/2016/07/22/how-to-extend-django-user-model.html#onetoone
@receiver(post_save, sender=User)
def create_user_teammember(sender, instance, created, **kwargs):
    if created:
        TeamMember.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_teammember(sender, instance, **kwargs):
    instance.teammember.save()