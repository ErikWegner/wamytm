import datetime
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, SuspiciousOperation
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import get_language_from_request

from ..model.Timerange import TimeRange, TimeRangeManager
from ..forms import AddTimeRangeForm


@login_required
def add(request):
    def handle_overlaps(form: AddTimeRangeForm):
        if form.cleaned_data['overlap_actions'] is None or form.cleaned_data['overlap_actions'] == "":
            return
        von = form.cleaned_data['start']
        end = form.cleaned_data['end'] if form.cleaned_data['end'] is not None else von
        kind = form.cleaned_data['kind']
        part = form.cleaned_data['part_of_day']

        overlaps = TimeRange.objects.overlapResolution(von, end, form.cleaned_data['user_id'], kind, part)

        overlaps_map = {}
        for m in overlaps['mods']:
            overlaps_map[m['item']['id']] = m['res']

        form_overlap_map = form.cleaned_data['overlap_actions']
        for f in form_overlap_map:
            fp = f.split(':')
            if len(fp) != 2:
                raise SuspiciousOperation()
            action = fp[1].lower()
            itemid = int(fp[0])
            if not itemid in overlaps_map or overlaps_map[itemid] != action:
                raise SuspiciousOperation()
            del(overlaps_map[itemid])

            if part is None or part == '':
                # Behandlung voller Tage
                if action == TimeRangeManager.OVERLAP_DELETE:
                    TimeRange.objects.get(id=itemid).delete()
                elif action == TimeRangeManager.OVERLAP_NEW_END:
                    item = TimeRange.objects.get(id=itemid)
                    item.bis = von + datetime.timedelta(days=-1)
                    item.save()
                elif action == TimeRangeManager.OVERLAP_NEW_START:
                    item = TimeRange.objects.get(id=itemid)
                    item.von = end + datetime.timedelta(days=1)
                    item.save()
                elif action == TimeRangeManager.OVERLAP_SPLIT:
                    prev_item = TimeRange.objects.get(id=itemid)
                    
                    # Create new item BEFORE modifying the old one to avoid history issues
                    next_item = TimeRange(
                        user=prev_item.user,
                        von=end + datetime.timedelta(days=1),
                        bis=prev_item.bis,
                        kind=prev_item.kind,
                        data=prev_item.data,
                        org_id=prev_item.org_id
                    )
                    
                    # Now modify the original item
                    prev_item.bis = von + datetime.timedelta(days=-1)
                    
                    prev_item.save()
                    next_item.save()
            else:
                # Vormittag/Nachmittag 
                if action == TimeRangeManager.OVERLAP_DELETE:
                    TimeRange.objects.get(id=itemid).delete()
                elif action == TimeRangeManager.OVERLAP_NEW_END:
                    item = TimeRange.objects.get(id=itemid)
                    if von > item.von:
                        item.bis = von + datetime.timedelta(days=-1)
                        item.save()
                    else:
                        # Wenn der neue Eintrag am gleichen Tag startet, auf anderen Tagesbereich setzen
                        data = item.safe_data()
                        data['partial'] = "a" if part == "f" else "f"
                        item.data = data
                        item.save()
                elif action == TimeRangeManager.OVERLAP_NEW_START:
                    item = TimeRange.objects.get(id=itemid)
                    if end < item.bis:
                        item.von = end + datetime.timedelta(days=1)
                        item.save()
                    else:
                        # Wenn der neue Eintrag am gleichen Tag endet, auf anderen Tagesbereich setzen
                        data = item.safe_data()
                        data['partial'] = "a" if part == "f" else "f"
                        item.data = data
                        item.save()
                elif action == TimeRangeManager.OVERLAP_SPLIT:
                    item = TimeRange.objects.get(id=itemid)
                    
                    if item.von < von:
                        # vor dem neuen Eintrag ist noch Luft
                        if item.bis > end:
                            # nach dem Eintrag ist noch Luft - echtes Split
                            next_item = TimeRange()
                            next_item.von = end + datetime.timedelta(days=1)
                            next_item.bis = item.bis
                            next_item.user = item.user
                            next_item.kind = item.kind
                            next_item.data = item.data
                            next_item.org_id = item.org_id
                            next_item.save()
                        
                        # Erstes Segment: bis vor den neuen Eintrag
                        item.bis = von + datetime.timedelta(days=-1)
                        item.save()
                        
                        # Teilzeit-Eintrag für den Tag des neuen Eintrags erstellen
                        if von == item.bis + datetime.timedelta(days=1):
                            partial_item = TimeRange()
                            partial_item.von = von
                            partial_item.bis = von  # gleicher Tag
                            partial_item.user = item.user
                            partial_item.kind = item.kind
                            partial_item.org_id = item.org_id
                            data = item.safe_data()
                            data['partial'] = "a" if part == "f" else "f"  # anderen Tagesbereich setzen
                            partial_item.data = data
                            partial_item.save()

                    elif item.bis > end:
                        # nach dem Eintrag ist noch Luft
                        if item.von < von:
                            # vor dem Eintrag ist noch Luft - echtes Split
                            prev_item = TimeRange()
                            prev_item.von = item.von
                            prev_item.bis = von + datetime.timedelta(days=-1)
                            prev_item.user = item.user
                            prev_item.kind = item.kind
                            prev_item.data = item.data
                            prev_item.org_id = item.org_id
                            prev_item.save()
                        
                        # Zweites Segment: ab nach dem neuen Eintrag
                        item.von = end + datetime.timedelta(days=1)
                        item.save()
                        
                        # Teilzeit-Eintrag für den Tag des neuen Eintrags erstellen
                        if end == item.von - datetime.timedelta(days=1):
                            partial_item = TimeRange()
                            partial_item.von = end
                            partial_item.bis = end  # gleicher Tag
                            partial_item.user = item.user
                            partial_item.kind = item.kind
                            partial_item.org_id = item.org_id
                            data = item.safe_data()
                            data['partial'] = "a" if part == "f" else "f"  # anderen Tagesbereich setzen
                            partial_item.data = data
                            partial_item.save()
                    else:
                        # vorhandener ganztägiger Eintrag wird zu Teilzeit-Eintrag
                        data = item.safe_data()
                        data['partial'] = "a" if part == "f" else "f"
                        item.data = data
                        item.save()

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