from django.contrib import admin

# Register your models here.

from .models import OrgUnit, ProductTeam

admin.site.register(OrgUnit)
admin.site.register(ProductTeam)
