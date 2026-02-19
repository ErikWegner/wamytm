import datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import get_language_from_request
from django.db import transaction

from ..forms import AddTimeRangeForm
from .overlap import handle_overlaps

@login_required
def add(request):
    if request.method == 'POST':
        form = AddTimeRangeForm(data=request.POST, user=request.user)
        if form.is_valid():
            # Check if periodic entry creation is requested
            create_periodic = request.POST.get('create_periodic') == 'on'
            periodic_end = request.POST.get('periodic_end')
            
            if create_periodic and periodic_end:
                # Create periodic entries
                try:
                    periodic_end_date = datetime.datetime.strptime(periodic_end, '%Y-%m-%d').date()
                    _create_periodic_entries(form, periodic_end_date)
                    return HttpResponseRedirect(reverse('wamytmapp:index'))
                except ValueError as e:
                    form.add_error(None, f"Ungültiges End-Datum: {e}")
                except ValidationError as e:
                    for field in e.message_dict.keys():
                        for error in e.message_dict[field]:
                            form.add_error(field, error)
            else:
                # Single entry creation (existing logic)
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


def _create_periodic_entries(form, end_date):
    """Create weekly periodic entries from start date to end date."""
    cleaned_data = form.cleaned_data
    start_date = cleaned_data['start']
    entry_end_date = cleaned_data['end'] if cleaned_data['end'] else start_date
    
    # Calculate the duration of one entry in days
    entry_duration = (entry_end_date - start_date).days
    
    current_start = start_date
    
    with transaction.atomic():
        while current_start <= end_date:
            current_end = current_start + datetime.timedelta(days=entry_duration)
            
            # Don't create entries beyond the periodic end date
            if current_start > end_date:
                break
            
            # Create a new form instance with the current dates
            entry_data = form.data.copy()
            entry_data['start'] = current_start.strftime('%Y-%m-%d')
            entry_data['end'] = current_end.strftime('%Y-%m-%d') if current_end != current_start else ''
            
            entry_form = AddTimeRangeForm(data=entry_data, user=form.user)
            
            if entry_form.is_valid():
                time_range = entry_form.get_time_range()
                time_range.full_clean()
                
                # Handle overlaps for each individual entry
                handle_overlaps(entry_form)
                
                time_range.save()
            else:
                # If any entry fails validation, raise an error
                raise ValidationError(f"Fehler beim Erstellen des Eintrags für {current_start}: {entry_form.errors}")
            
            # Move to next week
            current_start += datetime.timedelta(weeks=1)