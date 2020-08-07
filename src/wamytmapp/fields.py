from django import forms


class OverlapActionsField(forms.MultipleChoiceField):
    def valid_value(self, value):
        return True
