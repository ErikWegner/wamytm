from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

# Register your models here.

from .models import OrgUnit, TeamMember

admin.site.register(OrgUnit)

# Define an inline admin descriptor for TeamMember model
# which acts a bit like a singleton
class TeamMemberInline(admin.StackedInline):
    model = TeamMember
    can_delete = False
    verbose_name_plural = 'team members'

# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (TeamMemberInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)
