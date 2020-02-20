from django import forms
from .models import OrgUnit, TimeRange, TeamMember, user_display_name
from django.utils.translation import pgettext_lazy


class DateInput(forms.DateInput):
    input_type = 'date'


class AddTimeRangeForm(forms.Form):
    """
        A form to add a new time range entry.
    """
    dateInputAttrs = {
        'data-provide':'datepicker',
        'data-date-calendar-weeks': 'true',
        'data-date-format': 'yyyy-mm-dd',
        'data-date-today-highlight': 'true',
        'data-date-week-start': '1',
        'data-date-today-btn': 'true'
    }
    user = forms.CharField(
        label=pgettext_lazy('AddTimeRangeForm', 'User'),
        disabled=True,
        required=False,
    )
    start = forms.DateField(
        label=pgettext_lazy('AddTimeRangeForm', 'Start'),
        required=True,
        widget=forms.widgets.DateInput(attrs=dateInputAttrs))
    end = forms.DateField(
        label=pgettext_lazy('AddTimeRangeForm', 'End'),
        required=False,
        help_text=pgettext_lazy('AddTimeRangeForm',
                    'If left blank, it will be set to start date'),
        widget=forms.widgets.DateInput(attrs=dateInputAttrs)
    )
    orgunit_id = forms.ChoiceField(
        required=True,
        help_text=pgettext_lazy('AddTimeRangeForm', 'Entry will be visible to this and all organizational units above'),
        label=pgettext_lazy('AddTimeRangeForm', 'Organizational unit'))
    kind = forms.ChoiceField(
        required=True,
        label=pgettext_lazy('AddTimeRangeForm', 'Kind of time range'),
        choices=TimeRange.KIND_CHOICES
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(AddTimeRangeForm, self).__init__(*args, **kwargs)
        self.fields['user'].initial = user_display_name(self.user)
        self.fields['orgunit_id'].choices = OrgUnit.objects.selectListItems()
        self.fields['orgunit_id'].initial = TeamMember.objects.get(
            pk=self.user.id).orgunit_id

    def get_time_range(self):
        if self.is_valid() == False:
            return None

        cleaned_data = self.cleaned_data
        cleaned_data['user_id'] = self.user.id
        del(cleaned_data['user'])

        return TimeRange(**cleaned_data)


class OrgUnitFilterForm(forms.Form):
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
        self.fields['orgunit'].choices = OrgUnit.objects.selectListItemsWithAllChoice()


class ProfileForm(forms.Form):
    orgunit = forms.ChoiceField(
        required=True,
        help_text=pgettext_lazy('ProfileForm', 'Default value when adding new entries and for filter'),
        label=pgettext_lazy('ProfileForm', 'Organizational unit'))

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['orgunit'].choices = OrgUnit.objects.selectListItems()
        self.fields['orgunit'].initial = TeamMember.objects.get(
            pk=self.user.id).orgunit_id
