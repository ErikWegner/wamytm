from django.db import models

# Create your models here.


class OrgUnit(models.Model):
    name = models.CharField(max_length=80)

    def __str__(self):
        return self.name


class ProductTeam(models.Model):
    orgunit = models.ForeignKey(OrgUnit, on_delete=models.PROTECT)
    name = models.CharField(max_length=120)

    def __str__(self):
        return self.name
