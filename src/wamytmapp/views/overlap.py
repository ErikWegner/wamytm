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
from ..model.ODB import OMS
from .timerange_utils import extract_username, find_timerange, find_user_by_display_name

logger = logging.getLogger(__name__)


def _parse_date_yyyy_mm_dd(value, field_name):
    if isinstance(value, datetime.date):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field_name} muss ein Datum-String sein")
    try:
        return datetime.datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError as e:
        raise ValueError(f"{field_name} hat ein ungültiges Format (erwartet YYYY-MM-DD)") from e


def _clone_timerange(base_tr, *, von, bis, kind):
    data = dict(base_tr.data) if base_tr.data else {}
    # For this feature we only support full-day entries; enforce no partial.
    if data.get(TimeRange.DATA_PARTIAL):
        raise ValueError('Partial-Einträge werden für "Typ ändern" nicht unterstützt')
    data.pop(TimeRange.DATA_PARTIAL, None)
    return TimeRange(
        user=base_tr.user,
        von=von,
        bis=bis,
        kind=kind,
        data=data,
        org=base_tr.org
    )


def _user_default_org_id(user):
    try:
        m2o = OMS.objects.getORG_ID(user.id)
        return m2o.m2o_org_id if m2o is not None else None
    except Exception:
        return None


def _ensure_full_day_timerange(tr, context):
    if (tr.data or {}).get(TimeRange.DATA_PARTIAL):
        raise ValueError(f'Halbtägige Einträge werden bei "{context}" aktuell nicht unterstützt')


def _find_full_day_timerange_for_day(user, day):
    # Find a full-day TimeRange overlapping day for this user.
    candidates = list(TimeRange.objects.filter(user=user, von__lte=day, bis__gte=day))
    full_day = []
    for tr in candidates:
        if not (tr.data or {}).get(TimeRange.DATA_PARTIAL):
            full_day.append(tr)
    if len(full_day) > 1:
        raise ValueError('Mehrere ganztägige Einträge an diesem Tag gefunden')
    return full_day[0] if full_day else None


@require_http_methods(["POST"])
@login_required
def add_entry_at_day(request):
    """Create a new one-day entry at the given day and split an existing entry if needed.

    Expected payload:
    {
      "day": "YYYY-MM-DD",
      "new_kind": "a"|"p"|"m"
    }
    """
    try:
        data = json.loads(request.body)
        day = _parse_date_yyyy_mm_dd(data.get('day'), 'day')
        new_kind = (data.get('new_kind') or '').strip()

        if new_kind not in {'a', 'p', 'm'}:
            return JsonResponse({'success': False, 'error': 'Ungültiger Typ'}, status=400)

        existing = _find_full_day_timerange_for_day(request.user, day)

        undo_data = {
            'original': None,
            'created_ids': [],
        }

        with transaction.atomic():
            # Validate existing entry if present
            if existing is not None:
                _ensure_full_day_timerange(existing, 'Hinzufügen')
                if existing.kind == new_kind:
                    return JsonResponse({'success': False, 'error': 'Es existiert bereits ein Eintrag mit diesem Typ an dem Tag'}, status=400)

                undo_data['original'] = {
                    'deleted': False,
                    'id': existing.id,
                    'von': existing.von.strftime('%Y-%m-%d'),
                    'bis': existing.bis.strftime('%Y-%m-%d'),
                    'kind': existing.kind,
                    'data': dict(existing.data) if existing.data else {},
                    'org_id': existing.org_id,
                }

                original_von = existing.von
                original_bis = existing.bis
                old_kind = existing.kind

                # Remove the day from existing by shrinking/splitting
                if original_von == day and original_bis == day:
                    # Single-day existing -> delete
                    undo_data['original']['deleted'] = True
                    existing.delete()
                elif original_von == day:
                    existing.von = day + datetime.timedelta(days=1)
                    existing.save()
                elif original_bis == day:
                    existing.bis = day - datetime.timedelta(days=1)
                    existing.save()
                else:
                    # Split: keep existing as BEFORE, create AFTER
                    existing.bis = day - datetime.timedelta(days=1)
                    existing.save()
                    after_tr = _clone_timerange(existing, von=day + datetime.timedelta(days=1), bis=original_bis, kind=old_kind)
                    after_tr.save()
                    undo_data['created_ids'].append(after_tr.id)

                # Create the new one-day entry
                base_org = existing.org_id if existing is not None else _user_default_org_id(request.user)
                new_tr = TimeRange(
                    user=request.user,
                    von=day,
                    bis=day,
                    kind=new_kind,
                    data={'v': 1},
                    org_id=base_org
                )
                new_tr.save()
                undo_data['created_ids'].append(new_tr.id)
            else:
                # No existing full-day entry -> just create new
                base_org = _user_default_org_id(request.user)
                new_tr = TimeRange(
                    user=request.user,
                    von=day,
                    bis=day,
                    kind=new_kind,
                    data={'v': 1},
                    org_id=base_org
                )
                new_tr.save()
                undo_data['created_ids'].append(new_tr.id)

        return JsonResponse({'success': True, 'undo_data': undo_data})

    except ValueError as e:
        logger.error(f"ValueError in add_entry_at_day: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in add_entry_at_day: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Unerwarteter Fehler: {str(e)}'}, status=500)


@require_http_methods(["POST"])
@login_required
def undo_add_entry(request):
    """Undo the last 'Hinzufügen' operation.

    Expected payload:
    {
      "original": null | {"deleted": bool, "id": int, "von": "YYYY-MM-DD", "bis": "YYYY-MM-DD", "kind": "a", "data": {...}, "org_id": 123},
      "created_ids": [1,2]
    }
    """
    try:
        data = json.loads(request.body)
        original = data.get('original')
        created_ids = data.get('created_ids') or []

        with transaction.atomic():
            # Delete created entries
            if created_ids:
                TimeRange.objects.filter(user=request.user, id__in=created_ids).delete()

            if original:
                original_deleted = bool(original.get('deleted'))
                original_id = original.get('id')
                original_von = _parse_date_yyyy_mm_dd(original.get('von'), 'original.von')
                original_bis = _parse_date_yyyy_mm_dd(original.get('bis'), 'original.bis')
                original_kind = (original.get('kind') or '').strip()
                original_data = original.get('data') if isinstance(original.get('data'), dict) else {}
                original_org_id = original.get('org_id')

                if original_kind not in {'a', 'p', 'm'}:
                    return JsonResponse({'success': False, 'error': 'Ungültige Undo-Daten (kind)'}, status=400)

                if original_deleted:
                    restored = TimeRange(
                        user=request.user,
                        von=original_von,
                        bis=original_bis,
                        kind=original_kind,
                        data=original_data,
                        org_id=original_org_id
                    )
                    restored.save()
                else:
                    if original_id is None:
                        return JsonResponse({'success': False, 'error': 'Ungültige Undo-Daten (id)'}, status=400)
                    tr = TimeRange.objects.filter(user=request.user, id=original_id).first()
                    if not tr:
                        return JsonResponse({'success': False, 'error': 'Original-Eintrag nicht gefunden'}, status=404)
                    tr.von = original_von
                    tr.bis = original_bis
                    tr.kind = original_kind
                    tr.data = original_data
                    tr.org_id = original_org_id
                    tr.save()

        return JsonResponse({'success': True})

    except ValueError as e:
        logger.error(f"ValueError in undo_add_entry: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in undo_add_entry: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Unerwarteter Fehler: {str(e)}'}, status=500)


@require_http_methods(["POST"])
@login_required
def change_type_visible(request):
    """Change the kind/type of the currently visible slice of a TimeRange.

    Creates a new TimeRange with the new kind for the intersection of the clicked
    entry with the visible week range (Mo–Fr). The old entry is shortened/split
    into before/after segments with the old kind.

    Expected payload:
    {
      "target": {"user": "Nachname, Vorname (USERNAME)", "min_tag": "YYYY-MM-DD", "kind": "a", "partial": ""},
      "new_kind": "p",
      "visible_start": "YYYY-MM-DD",
      "visible_end": "YYYY-MM-DD"
    }
    """
    try:
        data = json.loads(request.body)
        target = data['target']
        new_kind = (data.get('new_kind') or '').strip()
        visible_start = _parse_date_yyyy_mm_dd(data.get('visible_start'), 'visible_start')
        visible_end = _parse_date_yyyy_mm_dd(data.get('visible_end'), 'visible_end')

        if visible_start > visible_end:
            return JsonResponse({'success': False, 'error': 'Ungültiger sichtbarer Zeitraum'}, status=400)

        if new_kind not in {'a', 'p', 'm'}:
            return JsonResponse({'success': False, 'error': 'Ungültiger Typ'}, status=400)

        # Only full-day entries supported for now.
        if (target.get('partial') or '').strip():
            return JsonResponse({'success': False, 'error': 'Halbtägige Einträge werden beim Typwechsel aktuell nicht unterstützt'}, status=400)

        old_tr = find_timerange(
            target['user'],
            target['min_tag'],
            (target.get('kind') or '').strip(),
            (target.get('partial') or '').strip()
        )

        if old_tr.user != request.user:
            return JsonResponse({'success': False, 'error': 'Sie können nur Ihre eigenen Einträge bearbeiten'}, status=403)

        if (old_tr.data or {}).get(TimeRange.DATA_PARTIAL):
            return JsonResponse({'success': False, 'error': 'Halbtägige Einträge werden beim Typwechsel aktuell nicht unterstützt'}, status=400)

        if old_tr.kind == new_kind:
            return JsonResponse({'success': False, 'error': 'Eintrag hat bereits diesen Typ'}, status=400)

        slice_start = max(old_tr.von, visible_start)
        slice_end = min(old_tr.bis, visible_end)
        if slice_start > slice_end:
            return JsonResponse({'success': False, 'error': 'Eintrag ist im sichtbaren Zeitraum nicht enthalten'}, status=400)

        original_von = old_tr.von
        original_bis = old_tr.bis
        old_kind = old_tr.kind
        original_data = dict(old_tr.data) if old_tr.data else {}
        original_org_id = old_tr.org_id

        undo_data = {
            'original': {
                'deleted': False,
                'id': old_tr.id,
                'von': original_von.strftime('%Y-%m-%d'),
                'bis': original_bis.strftime('%Y-%m-%d'),
                'kind': old_kind,
                'data': original_data,
                'org_id': original_org_id,
            },
            'created_ids': [],
        }

        with transaction.atomic():
            # Case: slice covers entire original -> delete old, create one new
            if slice_start == original_von and slice_end == original_bis:
                undo_data['original']['deleted'] = True
                old_tr.delete()
                new_tr = _clone_timerange(old_tr, von=slice_start, bis=slice_end, kind=new_kind)
                new_tr.save()
                undo_data['created_ids'] = [new_tr.id]
                return JsonResponse({'success': True, 'undo_data': undo_data})

            # Case: slice at start -> keep old as AFTER by moving start
            if slice_start == original_von and slice_end < original_bis:
                # Shrink old to after slice
                old_tr.von = slice_end + datetime.timedelta(days=1)
                old_tr.save()
                new_tr = _clone_timerange(old_tr, von=slice_start, bis=slice_end, kind=new_kind)
                new_tr.save()
                undo_data['created_ids'] = [new_tr.id]
                return JsonResponse({'success': True, 'undo_data': undo_data})

            # Case: slice at end -> keep old as BEFORE by moving end
            if slice_end == original_bis and slice_start > original_von:
                old_tr.bis = slice_start - datetime.timedelta(days=1)
                old_tr.save()
                new_tr = _clone_timerange(old_tr, von=slice_start, bis=slice_end, kind=new_kind)
                new_tr.save()
                undo_data['created_ids'] = [new_tr.id]
                return JsonResponse({'success': True, 'undo_data': undo_data})

            # Case: slice strictly inside -> split into before + after, plus new middle
            if slice_start > original_von and slice_end < original_bis:
                # Shrink old to BEFORE
                old_tr.bis = slice_start - datetime.timedelta(days=1)
                old_tr.save()

                after_tr = _clone_timerange(old_tr, von=slice_end + datetime.timedelta(days=1), bis=original_bis, kind=old_kind)
                after_tr.save()

                new_tr = _clone_timerange(old_tr, von=slice_start, bis=slice_end, kind=new_kind)
                new_tr.save()

                undo_data['created_ids'] = [after_tr.id, new_tr.id]
                return JsonResponse({'success': True, 'undo_data': undo_data})

            # Fallback (shouldn't happen)
            return JsonResponse({'success': False, 'error': 'Unerwarteter Fall beim Aufsplitten'}, status=500)

    except KeyError as e:
        logger.error(f"KeyError in change_type_visible: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Fehlende Daten: {str(e)}'}, status=400)
    except ValueError as e:
        logger.error(f"ValueError in change_type_visible: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in change_type_visible: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Unerwarteter Fehler: {str(e)}'}, status=500)


@require_http_methods(["POST"])
@login_required
def undo_change_type(request):
    """Undo the last "Typ ändern" operation.

    Expected payload (from sessionStorage):
    {
      "original": {"deleted": bool, "id": int, "von": "YYYY-MM-DD", "bis": "YYYY-MM-DD", "kind": "a", "data": {...}, "org_id": 123},
      "created_ids": [1,2]
    }
    """
    try:
        data = json.loads(request.body)
        original = data.get('original') or {}
        created_ids = data.get('created_ids') or []

        original_deleted = bool(original.get('deleted'))
        original_id = original.get('id')
        original_von = _parse_date_yyyy_mm_dd(original.get('von'), 'original.von')
        original_bis = _parse_date_yyyy_mm_dd(original.get('bis'), 'original.bis')
        original_kind = (original.get('kind') or '').strip()
        original_data = original.get('data') if isinstance(original.get('data'), dict) else {}
        original_org_id = original.get('org_id')

        if original_kind not in {'a', 'p', 'm'}:
            return JsonResponse({'success': False, 'error': 'Ungültige Undo-Daten (kind)'}, status=400)

        with transaction.atomic():
            # Delete any created entries (must belong to current user)
            if created_ids:
                TimeRange.objects.filter(user=request.user, id__in=created_ids).delete()

            if original_deleted:
                # Recreate original (since it was deleted)
                restored = TimeRange(
                    user=request.user,
                    von=original_von,
                    bis=original_bis,
                    kind=original_kind,
                    data=original_data,
                    org_id=original_org_id
                )
                restored.save()
            else:
                # Restore original by ID
                if original_id is None:
                    return JsonResponse({'success': False, 'error': 'Ungültige Undo-Daten (id)'}, status=400)

                tr = TimeRange.objects.filter(user=request.user, id=original_id).first()
                if not tr:
                    return JsonResponse({'success': False, 'error': 'Original-Eintrag nicht gefunden'}, status=404)

                tr.von = original_von
                tr.bis = original_bis
                tr.kind = original_kind
                tr.data = original_data
                tr.org_id = original_org_id
                tr.save()

        return JsonResponse({'success': True})

    except KeyError as e:
        logger.error(f"KeyError in undo_change_type: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Fehlende Daten: {str(e)}'}, status=400)
    except ValueError as e:
        logger.error(f"ValueError in undo_change_type: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in undo_change_type: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Unerwarteter Fehler: {str(e)}'}, status=500)


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