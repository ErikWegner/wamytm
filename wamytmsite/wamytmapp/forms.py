from django import forms
from .models import OrgUnit, TimeRange, TeamMember


class DateInput(forms.DateInput):
    input_type = 'date'


class AddTimeRangeForm(forms.Form):
    """
        A form to add a new time range entry.
    """
    user = forms.CharField(
        disabled=True
    )
    start = forms.DateField(
        required=True, widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(
        required=False, widget=forms.widgets.DateInput(attrs={'type': 'date'}))
    orgunit_id = forms.ChoiceField(
        required=True,
        choices=OrgUnit.objects.selectListItems(),
        label='Organizational unit')
    kind = forms.ChoiceField(
        required=True,
        label='Kind of time range',
        choices=TimeRange.KIND_CHOICES
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(AddTimeRangeForm, self).__init__(*args, **kwargs)
        self.fields['user'].initial = self.user.username
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
    orgunit = forms.ChoiceField(
        required=False,
        choices=OrgUnit.objects.selectListItemsWithAllChoice(),
        widget=forms.Select(
            attrs={'onchange': 'filterform.submit();'}
        ),
        label='Organizational unit')


class ProfileForm(forms.Form):
    orgunit = forms.ChoiceField(
        required=True,
        choices=OrgUnit.objects.selectListItems(),
        label='Organizational unit')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['orgunit'].initial = TeamMember.objects.get(
            pk=self.user.id).orgunit_id
