from django.contrib import admin
from django.contrib.admin.models import LogEntry
from django.contrib.admin.utils import quote
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import NoReverseMatch, reverse
from django.utils.translation import pgettext_lazy

from simple_history.admin import SimpleHistoryAdmin

from .model.Timerange import TimeRange
from .model.virtualteam import *
from .model.OrgUnit import *
from .model.ODB import *
from .model.sonst import *

from .forms import TimeRangeEditForm, orgs4wamytmEditForm

#admin.site.register(OrgUnit)
admin.site.register(TimeRange)
#admin.site.register(AllDayEvent)


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
    inlines = (OrgUnitDelegateInline,)


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
    readonly_fields = ('user', 'description_display')
    view_on_site = False
    list_display = ('von', 'bis', 'kind', 'description_display')
    list_filter = ('von', 'kind')
    date_hierarchy = 'von'
    ordering = ['-von']
    form = TimeRangeEditForm
    history_list_display = ['von', 'bis', 'kind']
    fields = ('org', 'von', 'bis', 'subkind', 'part_of_day', 'user', 'description_display')
    
    def description_display(self, obj):
        """Display description from JSON data field"""
        if obj and obj.data and TimeRange.DATA_DESCRIPTION in obj.data:
            return obj.data[TimeRange.DATA_DESCRIPTION] or '-'
        return '-'
    
    description_display.short_description = pgettext_lazy('TimeRange', 'Description')

    def has_module_permission(self, request):
        return True

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        if obj is None:
            return True  # False will be interpreted as meaning that the current user is not permitted to view any object of this type
        return self._isAccessAllowed(request, obj)

    def has_change_permission(self, request, obj=None):
        return False #self._isAccessAllowed(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._isAccessAllowed(request, obj)

    def _isAccessAllowed(self, request, obj=None):
        if obj is None:
            return False
        if obj.user_id == request.user.id:
            return True
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList(
            request.user.id)
        if obj.org_id in delegatedOUList:
            return True
        return False

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        delegatedOUList = OrgUnitDelegate.objects.delegatedOUIdList(request.user.id)
        return qs.filter(
            Q(user=request.user) | Q(org_id__in=delegatedOUList)
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
    fields = ('username', 'last_name', 'first_name',)
    readonly_fields = ('username', 'last_name', 'first_name',)
    inlines = (OrgUnitDelegateInline,)

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
        user_org = OMS.objects.getORG_ID(obj.id)
        if user_org is None:
            return None
        # Get the org unit name from the mv_odb_org table
        org_record = mv_odb_org.objects.filter(m_org_id=user_org.m2o_org_id).first()
        return org_record.m_org if org_record else None

class KindAdmin(admin.ModelAdmin):
    list_display = [ 'kind', 'wertung' ]
    readonly_fields = [ 'kind' ]
    ordering = ['-wertung']
    def has_delete_permission(self, request, obj=None):
        return False
    
class virtualteamAdmin(admin.ModelAdmin):
    list_display = [ 'vt_name', 'vt_parent_id' ]
    ordering = ['-vt_id']
    readonly_fields = [ 'vt_id' ]
    def has_delete_permission(self, request, obj=None):
        return False

class ma2vtAdmin(admin.ModelAdmin):
    #list_display = [ 'vt_id', 'user_id' ]
    list_filter = ["vt"]
    #pass

class orgs4wamytmAdmin(admin.ModelAdmin):
    list_display = [ 'm_org' ]
    form = orgs4wamytmEditForm


korporator_admin.register(AllDayEvent, AllDayEventAdmin)
#korporator_admin.register(OrgUnit)
korporator_admin.register(KIND, KindAdmin)
korporator_admin.register(orgs4wamytm, orgs4wamytmAdmin)
korporator_admin.register(User, DelegatesAdmin)
korporator_admin.register(virtualteam, virtualteamAdmin)
korporator_admin.register(ma2vt, ma2vtAdmin)