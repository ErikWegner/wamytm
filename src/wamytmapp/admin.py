from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import pgettext_lazy

from .models import OrgUnit, TeamMember, TimeRange, AllDayEvent, OrgUnitDelegate
from .forms import TimeRangeEditForm

admin.site.register(OrgUnit)
admin.site.register(TimeRange)
admin.site.register(AllDayEvent)


class TeamMemberInline(admin.StackedInline):
    model = TeamMember
    can_delete = False
    verbose_name_plural = 'team members'


class OrgUnitDelegateInline(admin.TabularInline):
    model = OrgUnitDelegate
    verbose_name = 'Delete for this organizational unit'
    verbose_name_plural = 'Delegate for these organizational units'


class UserAdmin(BaseUserAdmin):
    inlines = (TeamMemberInline, OrgUnitDelegateInline)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class BasicAdminSite(admin.AdminSite):
    site_header = "Korporator"
    index_title = pgettext_lazy("Admin site", "Korporator administration area")

    def has_permission(self, request):
        return request.user is not None and request.user.is_authenticated


korporator_admin = BasicAdminSite(name="ka")


class TimeRangeBasicAdmin(admin.ModelAdmin):
    readonly_fields = ('user',)
    view_on_site = False
    list_display = ('start', 'end', 'kind')
    list_filter = ('start', 'kind')
    date_hierarchy = 'start'
    ordering = ['-start']
    form = TimeRangeEditForm

    def has_module_permission(self, request):
        return True

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return True  # False will be interpreted as meaning that the current user is not permitted to view any object of this type
        return self._isOwner(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._isOwner(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._isOwner(request, obj)

    def _isOwner(self, request, obj=None):
        if obj is None:
            return False
        return obj.user_id == request.user.id

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(user=request.user)


korporator_admin.register(TimeRange, TimeRangeBasicAdmin)


class AllDayEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'day'
    list_display = ('day', 'description')
    list_filter = ('description',)
    ordering = ['-day']
    search_fields = ['description']


korporator_admin.register(AllDayEvent, AllDayEventAdmin)
korporator_admin.register(OrgUnit)
