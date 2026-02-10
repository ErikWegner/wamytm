import datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import get_language_from_request

from ..forms import AddTimeRangeForm
from .overlap import handle_overlaps

@login_required
def add(request):
    if request.method == 'POST':
        form = AddTimeRangeForm(data=request.POST, user=request.user)
        if form.is_valid():
            time_range = form.get_time_range()
            try:
                time_range.full_clean()
                handle_overlaps(form)
                time_range.save()
                return HttpResponseRedirect(reverse('wamytmapp:index'))
            except ValidationError as e:
                for field in e.message_dict.keys():
                    for error in e.message_dict[field]:
                        form.add_error(field, error)
    else:
        form = AddTimeRangeForm(user=request.user)
        
    language = get_language_from_request(request)
    if language is not None and language.startswith("de"):
        form.fields['start'].widget.attrs['data-date-language'] = 'de'
        form.fields['end'].widget.attrs['data-date-language'] = 'de'

    return render(request, 'wamytmapp/add2.html', {'form': form})