from django import forms
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.utils.translation import pgettext_lazy

from .fields import OverlapActionsField
from .models import mv_odb_org, OrgUnit, OrgUnitDelegate, TimeRange, TeamMember, user_display_name, OMS, ODB_STRUKT
from .config import RuntimeConfig


class DateInput(forms.DateInput):
    input_type = 'date'

class orgs4wamytmEditForm(forms.ModelForm):
    ko_m = forms.ChoiceField(
        required=True,
        #choices = ODB_STRUKT.objects.SelectList_with_Orgs(),
        label=pgettext_lazy('OrgUnitFilterForm', 'Organizational unit'))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['ko_m'].choices = ODB_STRUKT.objects.SelectList_with_Orgs()

class TimeRangeEditForm(forms.ModelForm):
    description = forms.CharField(
        max_length=150,
        required=False,
        label=pgettext_lazy('AddTimeRangeForm', 'Description'))
    part_of_day = forms.ChoiceField(
        help_text=pgettext_lazy(
            'AddTimeRangeForm', 'Entry can be associated to a part of the day'),
        label=pgettext_lazy('AddTimeRangeForm', 'Partial entry'),
        required=False,
        choices=[
            (None, pgettext_lazy('AddTimeRangeForm', 'Whole day')),
            ('f', pgettext_lazy('AddTimeRangeForm', 'Forenoon')),
            ('a', pgettext_lazy('AddTimeRangeForm', 'Afternoon'))
        ])
    subkind = forms.ChoiceField(
        required=True,
        label=pgettext_lazy('AddTimeRangeForm', 'Kind of time range'),
        choices=RuntimeConfig().TimeRangeChoices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs['instance']
        if instance and instance.data:
            if 'v' in instance.data:
                if TimeRange.DATA_DESCRIPTION in instance.data:
                    self.fields['description'].initial = instance.data[TimeRange.DATA_DESCRIPTION]
                if TimeRange.DATA_PARTIAL in instance.data:
                    self.fields['part_of_day'].initial = instance.data[TimeRange.DATA_PARTIAL]
        self.fields['subkind'].initial = instance.kind + "_"

    class Meta:
        model = TimeRange
        fields = ['orgunit', 'start', 'end', 'subkind',
                  'part_of_day', 'description', 'user']

    def clean(self):
        super().clean()
        cleaned_data = self.cleaned_data
        complexKind = cleaned_data['subkind']
        cleaned_data['kind'] = complexKind[:1]
        jsondata = {'v': 1}
        if 'description' in cleaned_data and cleaned_data['description'] != '':
            jsondata[TimeRange.DATA_DESCRIPTION] = cleaned_data['description']
        if 'part_of_day' in cleaned_data and cleaned_data['part_of_day'] != '':
            jsondata[TimeRange.DATA_PARTIAL] = cleaned_data['part_of_day']
        self.cleaned_data['data'] = jsondata

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.data = self.cleaned_data['data']
        instance.kind = self.cleaned_data['kind']
        return super().save(commit)


class AddTimeRangeForm(forms.Form):
    """
        A form to add a new time range entry.
    """
    dateInputAttrs = {
        'data-provide': 'datepicker',
        'data-date-calendar-weeks': 'true',
        'data-date-format': 'yyyy-mm-dd',
        'data-date-today-highlight': 'true',
        'data-date-week-start': '1',
        'data-date-today-btn': 'true'
    }
    required_css_class = 'required'
    user = forms.ChoiceField(
        label=pgettext_lazy('AddTimeRangeForm', 'User'),
        disabled=True,
        required=False)
    start = forms.DateField(
        label=pgettext_lazy('AddTimeRangeForm', 'Start'),
        required=True,
        widget=forms.widgets.DateInput(attrs=dateInputAttrs))
    end = forms.DateField(
        label=pgettext_lazy('AddTimeRangeForm', 'End'),
        required=False,
        help_text=pgettext_lazy('AddTimeRangeForm',
                                'If left blank, it will be set to start date'),
        widget=forms.widgets.DateInput(attrs=dateInputAttrs))
    #orgunit_id = forms.ChoiceField(
    org_id = forms.ChoiceField(
        required=True,
        disabled=False,
        help_text=pgettext_lazy(
            'AddTimeRangeForm', 'Entry will be visible to this and all organizational units above'),
        label=pgettext_lazy('AddTimeRangeForm', 'Organizational unit'))
    kind = forms.ChoiceField(
        required=True,
        label=pgettext_lazy('AddTimeRangeForm', 'Kind of time range'))
    description = forms.CharField(
        max_length=150,
        required=False,
        label=pgettext_lazy('AddTimeRangeForm', 'Description'))
    part_of_day = forms.ChoiceField(
        help_text=pgettext_lazy(
            'AddTimeRangeForm', 'Entry can be associated to a part of the day'),
        label=pgettext_lazy('AddTimeRangeForm', 'Partial entry'),
        required=False,
        choices=[
            (None, pgettext_lazy('AddTimeRangeForm', 'Whole day')),
            ('f', pgettext_lazy('AddTimeRangeForm', 'Forenoon')),
            ('a', pgettext_lazy('AddTimeRangeForm', 'Afternoon'))
        ])
    overlap_actions = OverlapActionsField(
        required=False
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.can_delegate = self.user.orgunitdelegate_set.count() > 0
        super(AddTimeRangeForm, self).__init__(*args, **kwargs)
        self.fields['user'].initial = self.user.id
        self.fields['user'].choices = [(self.user.id, user_display_name(self.user))]


        #self.fields['orgunit_id'].choices = odb_org.objects.selectListItemsWithAllChoice()
        self.fields['org_id'].choices = mv_odb_org.objects.selectListItemsWithAllChoice()
        M2O_ORG_ID = OMS.objects.getORG_ID(self.user.id)
        if M2O_ORG_ID is not None:
            #self.fields['orgunit_id'].initial = M2O_ORG_ID.M2O_ORG_ID
            self.fields['org_id'].initial = M2O_ORG_ID.m2o_org_id
            #self.fields['orgunit_id'].disabled = True
            self.fields['org_id'].disabled = True
        
        self._setupKindChoices()
        if self.can_delegate:
            userfield = self.fields['user']
            userfield.disabled = False
            userfield.required = True
            userfield.choices = map(lambda u: (u.user.id, user_display_name(
                u.user) + F" ({u.orgunit.name})"), OrgUnitDelegate.objects.delegatedUsers(self.user.id))

    def get_time_range(self):
        if self.is_valid() == False:
            return None

        cleaned_data = self.cleaned_data
        cleaned_data['user_id'] = cleaned_data['user'] if self.can_delegate else self.user.id
        del(cleaned_data['user'])
        complexKind = cleaned_data['kind']
        cleaned_data['kind'] = complexKind[:1]
        jsondata = {'v': 1}
        if complexKind[1:] != RuntimeConfig.KIND_DEFAULT:
            jsondata[TimeRange.DATA_KINDDETAIL] = complexKind[1:]
        if 'description' in cleaned_data and cleaned_data['description'] != '':
            jsondata[TimeRange.DATA_DESCRIPTION] = cleaned_data['description']
        if 'part_of_day' in cleaned_data and cleaned_data['part_of_day'] != '':
            jsondata[TimeRange.DATA_PARTIAL] = cleaned_data['part_of_day']
        initData = {
            'user_id': cleaned_data['user_id'],
            #'orgunit_id': cleaned_data['orgunit_id'],
            'org_id': cleaned_data['org_id'],
            'start': cleaned_data['start'],
            'end': cleaned_data['end'],
            'kind': complexKind[:1],
            'data': jsondata
        }
        return TimeRange(**initData)

    def _setupKindChoices(self):
        self.fields['kind'].choices = RuntimeConfig().TimeRangeChoices


class FrontPageFilterForm(forms.Form):
    embed = forms.BooleanField(required=False, widget=forms.HiddenInput())
    weekdelta = forms.IntegerField(required=False, widget=forms.HiddenInput())
    users = forms.CharField(required=False, widget=forms.HiddenInput())
    orgunit = forms.ChoiceField(
        required=False,
        widget=forms.Select(
            attrs={'onchange': 'submitFilter();'}
        ),
        label=pgettext_lazy('OrgUnitFilterForm', 'Organizational unit'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['orgunit'].choices = mv_odb_org.objects.selectListItemsWithAllChoice()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data['weekdelta'] is None:
            cleaned_data['weekdelta'] = 0


class OrgUnitFilterForm(forms.Form):
    embed = forms.BooleanField(required=False, widget=forms.HiddenInput())
    fd = forms.CharField(required=False, widget=forms.HiddenInput())
    td = forms.CharField(required=False, widget=forms.HiddenInput())
    orgunit = forms.ChoiceField(
        required=False,
        widget=forms.Select(
            attrs={'onchange': 'filterform.submit();'}
        ),
        label=pgettext_lazy('OrgUnitFilterForm', 'Organizational unit'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.fields['orgunit'].choices = OrgUnit.objects.selectListItemsWithAllChoice()
        self.fields['orgunit'].choices = mv_odb_org.objects.selectListItemsWithAllChoice()


class ProfileForm(forms.Form):
    orgunit = forms.ChoiceField(
        required=True,
        help_text=pgettext_lazy(
            'ProfileForm', 'Default value when adding new entries and for filter'),
        label=pgettext_lazy('ProfileForm', 'Organizational unit'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['orgunit'].choices = OrgUnit.objects.selectListItems()
        self.fields['orgunit'].initial = TeamMember.objects.get(
            pk=self.user.id).orgunit_id


class ConflictCheckForm(forms.Form):
    start = forms.DateField(
        label=pgettext_lazy('ConflictCheckForm', 'Start'),
        required=True)
    end = forms.DateField(
        label=pgettext_lazy('ConflictCheckForm', 'End'),
        required=True)
    uid = forms.IntegerField(
        required=False
    )
    kind = forms.CharField(required=True)
    part = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request")
        super(ConflictCheckForm, self).__init__(*args, **kwargs)

    def clean_uid(self):
        conflict_check_user_id = self.cleaned_data['uid']
        if conflict_check_user_id is None:
            self.cleaned_data['uid'] = self.request.user.id
            return
        logged_in_user_id = self.request.user.id
        if self.cleaned_data['uid'] == logged_in_user_id:
            return conflict_check_user_id
        if OrgUnitDelegate.objects.isDelegateForUser(
                self.request,
                User.objects.get(pk=conflict_check_user_id)):
            return self.cleaned_data['uid']
        raise PermissionDenied('uid invalid')
