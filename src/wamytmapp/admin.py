from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.utils import quote
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext_lazy

from simple_history.admin import SimpleHistoryAdmin

from .models import OrgUnit, TeamMember, TimeRange, AllDayEvent, OrgUnitDelegate
from .forms import TimeRangeEditForm

admin.site.register(OrgUnit)
admin.site.register(TimeRange)
admin.site.register(AllDayEvent)


class TeamMemberInline(admin.StackedInline):
    model = TeamMember
    can_delete = False
    verbose_name_plural = 'team members'

    def has_add_permission(self, request, obj=None):
        return self._hasPermission(request)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return self._hasPermission(request)

    def has_module_permission(self, request):
        return self._hasPermission(request)

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return True  # False will be interpreted as meaning that the current user is not permitted to view any object of this type
        return self._hasPermission(request)

    def _hasPermission(self, request):
        return request.user.has_perm('wamytmapp.assign_delegates')


class OrgUnitDelegateInline(admin.TabularInline):
    model = OrgUnitDelegate
    verbose_name = pgettext_lazy(
        "Admin site", 'Delegate for an organizational unit')
    verbose_name_plural = pgettext_lazy(
        "Admin site", 'Delegate for these organizational units')

    def has_add_permission(self, request, obj=None):
        return self._hasPermission(request)

    def has_delete_permission(self, request, obj=None):
        return self._hasPermission(request)

    def has_change_permission(self, request, obj=None):
        return self._hasPermission(request)

    def has_module_permission(self, request):
        return self._hasPermission(request)

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return True  # False will be interpreted as meaning that the current user is not permitted to view any object of this type
        return self._hasPermission(request)

    def _hasPermission(self, request):
        return request.user.has_perm('wamytmapp.assign_delegates')


class UserAdmin(BaseUserAdmin):
    inlines = (TeamMemberInline, OrgUnitDelegateInline)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class BasicAdminSite(admin.AdminSite):
    site_header = "Korporator"
    index_title = pgettext_lazy("Admin site", "Korporator administration area")
    index_template = "ka/index.html"

    def has_permission(self, request):
        return request.user is not None and request.user.is_authenticated


korporator_admin = BasicAdminSite(name="ka")


class TimeRangeBasicAdmin(SimpleHistoryAdmin):
    readonly_fields = ('user',)
    view_on_site = False
    list_display = ('start', 'end', 'kind')
    list_filter = ('start', 'kind')
    date_hierarchy = 'start'
    ordering = ['-start']
    form = TimeRangeEditForm
    history_list_display = ['start', 'end', 'kind']

    def has_module_permission(self, request):
        return True

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return True  # False will be interpreted as meaning that the current user is not permitted to view any object of this type
        return self._isAccessAllowed(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._isAccessAllowed(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._isAccessAllowed(request, obj)

    def _isAccessAllowed(self, request, obj=None):
        if obj is None:
            return False
        if obj.user_id == request.user.id:
            return True
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList(
            request.user.id)
        if obj.orgunit_id in delegatedOUList:
            return True
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList(
            request.user.id)
        return qs.filter(
            Q(user=request.user) | Q(orgunit__id__in=delegatedOUList)
        )


korporator_admin.register(TimeRange, TimeRangeBasicAdmin)


class AllDayEventAdmin(admin.ModelAdmin):
    date_hierarchy = 'day'
    list_display = ('day', 'description')
    list_filter = ('description',)
    ordering = ['-day']
    search_fields = ['description']


class DelegatesAdmin(admin.ModelAdmin):
    list_display = ('username', 'last_name', 'first_name', 'org_unit')
    list_filter = ('teammember__orgunit__name',)
    fields = ('username', 'last_name', 'first_name',)
    readonly_fields = ('username', 'last_name', 'first_name',)
    inlines = (TeamMemberInline, OrgUnitDelegateInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return self._hasPermission(request)

    def has_module_permission(self, request):
        return self._hasPermission(request)

    def has_view_permission(self, request, obj=None):
        return self._hasPermission(request)

    def _hasPermission(self, request):
        return request.user.has_perm('wamytmapp.assign_delegates')

    def org_unit(self, obj):
        if obj.teammember.orgunit is None:
            return None
        return obj.teammember.orgunit.name


korporator_admin.register(AllDayEvent, AllDayEventAdmin)
korporator_admin.register(OrgUnit)
korporator_admin.register(User, DelegatesAdmin)
