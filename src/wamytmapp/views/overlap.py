import json
import datetime
import logging
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError, SuspiciousOperation
from wamytmapp.model.Timerange import TimeRange, TimeRangeManager
from wamytmapp.forms import AddTimeRangeForm
from ..model.Timerange import TimeRange
from .timerange_utils import extract_username, find_timerange, find_user_by_display_name

logger = logging.getLogger(__name__)


@require_http_methods(["POST"])
@login_required
def resize_entry(request):
    """
    Adjust the duration of two adjacent TimeRange entries.
    
    Expected payload:
    {
        "center": {
            "user": "Nachname, Vorname (USERNAME)",
            "min_tag": "2026-02-11",
            "kind": "a",
            "partial": "f",
            "new_span": 2
        },
        "neighbor": {
            "user": "Nachname, Vorname (USERNAME)",
            "min_tag": "2026-02-12",
            "kind": "p",
            "partial": "",
            "new_span": 3
        },
        "side": "right"  // or "left"
    }
    """
    try:
        data = json.loads(request.body)
        logger.info(f"Resize request data: {data}")
        
        center_data = data['center']
        neighbor_data = data['neighbor']
        side = data['side']
        
        # Find TimeRange objects
        logger.info(f"Looking for center: user={center_data['user']}, min_tag={center_data['min_tag']}, kind={center_data['kind']}, partial={center_data['partial']}")
        center_tr = find_timerange(
            center_data['user'],
            center_data['min_tag'],
            center_data['kind'],
            center_data['partial']
        )
        logger.info(f"Found center: {center_tr}")
        
        logger.info(f"Looking for neighbor: user={neighbor_data['user']}, min_tag={neighbor_data['min_tag']}, kind={neighbor_data['kind']}, partial={neighbor_data['partial']}")
        neighbor_tr = find_timerange(
            neighbor_data['user'],
            neighbor_data['min_tag'],
            neighbor_data['kind'],
            neighbor_data['partial']
        )
        logger.info(f"Found neighbor: {neighbor_tr}")
        
        # Security check: user can only modify their own entries
        if center_tr.user != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Sie können nur Ihre eigenen Einträge bearbeiten'
            }, status=403)
        
        # Store original values for undo
        undo_data = {
            'center': {
                'user': center_data['user'],
                'min_tag': center_data['min_tag'],
                'kind': center_data['kind'],
                'partial': center_data['partial'],
                'old_von': center_tr.von.strftime('%Y-%m-%d'),
                'old_bis': center_tr.bis.strftime('%Y-%m-%d')
            },
            'neighbor': {
                'user': neighbor_data['user'],
                'min_tag': neighbor_data['min_tag'],
                'kind': neighbor_data['kind'],
                'partial': neighbor_data['partial'],
                'old_von': neighbor_tr.von.strftime('%Y-%m-%d'),
                'old_bis': neighbor_tr.bis.strftime('%Y-%m-%d')
            },
            'side': side
        }
        
        # Calculate old spans
        old_center_span = (center_tr.bis - center_tr.von).days + 1
        old_neighbor_span = (neighbor_tr.bis - neighbor_tr.von).days + 1
        
        logger.info(f"Old spans: center={old_center_span}, neighbor={old_neighbor_span}, side={side}")
        
        # Validation: The new_span values from frontend represent VISUAL spans (grid display)
        # which may be truncated for long entries. With delta-based calculation, we just
        # shift boundaries, so sum validation is not applicable.
        # Only validate that the resulting entry doesn't exceed 5 days visible span.
        
        delta = data.get('delta', 0)
        logger.info(f"Delta from frontend: {delta}")
        
        # Validate new_span is reasonable (0-5 days, where 0 means delete)
        if center_data['new_span'] > 5:
            return JsonResponse({
                'success': False,
                'error': f'Der Eintrag würde zu lang ({center_data["new_span"]} Tage). Maximum sind 5 Tage.'
            })
        
        # Validate: new spans must be at least 0 (0 means entry will be deleted)
        if center_data['new_span'] < 0 or neighbor_data['new_span'] < 0:
            return JsonResponse({
                'success': False,
                'error': 'SPAN darf nicht negativ sein'
            })
        
        # Log if entries will be deleted
        if center_data['new_span'] == 0:
            logger.info("Center will be deleted (new_span=0)")
        if neighbor_data['new_span'] == 0:
            logger.info("Neighbor will be deleted (new_span=0)")
        
        # Calculate new dates using 'delta' passed from frontend
        # delta > 0: dragged Right
        # delta < 0: dragged Left
        delta = data.get('delta', 0)
        logger.info(f"Applying delta={delta} (side={side})")
        
        with transaction.atomic():
            if side == 'right':
                # Dragging right edge: center grows/shrinks
                # Boundary moves by delta days
                # Center END moves
                center_tr.bis = center_tr.bis + datetime.timedelta(days=delta)
                # Neighbor START moves
                neighbor_tr.von = neighbor_tr.von + datetime.timedelta(days=delta)
                
                logger.info(f"Right edge: center.bis={center_tr.bis}, neighbor.von={neighbor_tr.von}")
            else:
                # Dragging left edge: center grows/shrinks
                # Boundary moves by delta days
                # Neighbor END moves
                neighbor_tr.bis = neighbor_tr.bis + datetime.timedelta(days=delta)
                # Center START moves
                center_tr.von = center_tr.von + datetime.timedelta(days=delta)
                
                logger.info(f"Left edge: neighbor.bis={neighbor_tr.bis}, center.von={center_tr.von}")
            
            # Validation: Start must be <= End
            # If either entry becomes invalid (von > bis), delete it
            center_deleted = False
            neighbor_deleted = False
            
            if center_tr.von > center_tr.bis:
                logger.info(f"Center would be invalid ({center_tr.von}-{center_tr.bis}), deleting it")
                center_tr.delete()
                center_deleted = True
            else:
                center_tr.save()
                logger.info(f"Saved center: {center_tr.von} - {center_tr.bis}")
            
            if neighbor_tr.von > neighbor_tr.bis:
                logger.info(f"Neighbor would be invalid ({neighbor_tr.von}-{neighbor_tr.bis}), deleting it")
                neighbor_tr.delete()
                neighbor_deleted = True
            else:
                neighbor_tr.save()
                logger.info(f"Saved neighbor: {neighbor_tr.von} - {neighbor_tr.bis}")
            
            if center_deleted and neighbor_deleted:
                logger.warning("Both entries deleted - this should not happen!")
            elif center_deleted:
                logger.info(f"Result: center DELETED, neighbor({neighbor_tr.von} - {neighbor_tr.bis})")
            elif neighbor_deleted:
                logger.info(f"Result: center({center_tr.von} - {center_tr.bis}), neighbor DELETED")
            else:
                logger.info(f"Result: center({center_tr.von} - {center_tr.bis}), neighbor({neighbor_tr.von} - {neighbor_tr.bis})")
        
        return JsonResponse({
            'success': True,
            'undo_data': undo_data
        })
        
    except KeyError as e:
        logger.error(f"KeyError in resize_entry: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Fehlende Daten: {str(e)}'
        }, status=400)
    except ValueError as e:
        logger.error(f"ValueError in resize_entry: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in resize_entry: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': f'Unerwarteter Fehler: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@login_required
def undo_resize(request):
    """
    Undo the last resize operation.
    
    Expected payload (from sessionStorage):
    {
        "center": {
            "user": "...",
            "min_tag": "...",
            "kind": "...",
            "partial": "...",
            "old_von": "2026-02-11",
            "old_bis": "2026-02-12"
        },
        "neighbor": {
            "user": "...",
            "min_tag": "...",
            "kind": "...",
            "partial": "...",
            "old_von": "2026-02-13",
            "old_bis": "2026-02-14"
        }
    }
    """
    try:
        data = json.loads(request.body)
        center_data = data['center']
        neighbor_data = data['neighbor']
        
        # Find current TimeRange objects (they may have moved)
        # We need to find them by user/kind/partial and dates close to old dates
        center_username_display = extract_username(center_data['user'])
        neighbor_username_display = extract_username(neighbor_data['user'])
        
        if not center_username_display:
            return JsonResponse({
                'success': False,
                'error': 'Ungültiger Benutzername für Center'
            }, status=400)
        
        # Find users using shared utility function
        try:
            center_user = find_user_by_display_name(center_username_display)
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=404)
        
        # Security check
        if center_user != request.user:
            return JsonResponse({
                'success': False,
                'error': 'Sie können nur Ihre eigenen Einträge bearbeiten'
            }, status=403)
        
        # Find neighbor user using shared utility function
        try:
            neighbor_user = find_user_by_display_name(neighbor_username_display)
        except ValueError as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=404)
        
        # Parse old dates
        center_old_von = datetime.datetime.strptime(center_data['old_von'], '%Y-%m-%d').date()
        center_old_bis = datetime.datetime.strptime(center_data['old_bis'], '%Y-%m-%d').date()
        neighbor_old_von = datetime.datetime.strptime(neighbor_data['old_von'], '%Y-%m-%d').date()
        neighbor_old_bis = datetime.datetime.strptime(neighbor_data['old_bis'], '%Y-%m-%d').date()
        
        # Find TimeRange entries - they should overlap with the old date range
        center_candidates = TimeRange.objects.filter(
            user=center_user,
            kind=center_data['kind'],
            von__lte=center_old_bis,
            bis__gte=center_old_von
        )
        
        # Filter by partial
        center_tr = None
        for tr in center_candidates:
            tr_partial = tr.data.get(TimeRange.DATA_PARTIAL, '') if tr.data else ''
            if tr_partial == center_data['partial']:
                center_tr = tr
                break
        
        if not center_tr:
            return JsonResponse({
                'success': False,
                'error': 'Center-Eintrag nicht gefunden'
            }, status=404)
        
        # Find neighbor
        neighbor_candidates = TimeRange.objects.filter(
            user=neighbor_user,
            kind=neighbor_data['kind'],
            von__lte=neighbor_old_bis,
            bis__gte=neighbor_old_von
        )
        
        neighbor_tr = None
        for tr in neighbor_candidates:
            tr_partial = tr.data.get(TimeRange.DATA_PARTIAL, '') if tr.data else ''
            if tr_partial == neighbor_data['partial']:
                neighbor_tr = tr
                break
        
        if not neighbor_tr:
            return JsonResponse({
                'success': False,
                'error': 'Nachbar-Eintrag nicht gefunden'
            }, status=404)
        
        # Restore old dates
        with transaction.atomic():
            center_tr.von = center_old_von
            center_tr.bis = center_old_bis
            neighbor_tr.von = neighbor_old_von
            neighbor_tr.bis = neighbor_old_bis
            
            center_tr.save()
            neighbor_tr.save()
        
        return JsonResponse({'success': True})
        
    except KeyError as e:
        return JsonResponse({
            'success': False,
            'error': f'Fehlende Daten: {str(e)}'
        }, status=400)
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Benutzer nicht gefunden'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Unerwarteter Fehler: {str(e)}'
        }, status=500)


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