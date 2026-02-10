"""
Utility functions for TimeRange operations.
Shared between overlap resolution and resize operations.
"""
import datetime
import logging
from django.contrib.auth.models import User
from wamytmapp.model.Timerange import TimeRange

logger = logging.getLogger(__name__)


def extract_username(user_display_name):
    """
    Extract username from format: 'Nachname, Vorname (USERNAME)'
    The USERNAME is displayed as: request.user.username.upper()[1:]
    So we need to find the full username in the database.
    
    Args:
        user_display_name: Display name in format "Nachname, Vorname (USERNAME)"
    
    Returns:
        str: Username part without prefix (e.g., "F9616" from "rf9616")
        None: If format is invalid
    """
    if not user_display_name:
        return None
    
    # Find username in parentheses
    start = user_display_name.find('(')
    end = user_display_name.find(')')
    
    if start != -1 and end != -1:
        username_part = user_display_name[start+1:end].strip()
        # This is username[1:].upper(), so we need to find the original username
        # We'll search for users where username[1:].upper() matches this
        return username_part
    
    return None


def find_user_by_display_name(username_display):
    """
    Find a User object from the display name part (username without prefix).
    
    Args:
        username_display: Username display (e.g., "F9616")
    
    Returns:
        User: Django User object
    
    Raises:
        ValueError: If user not found
    """
    if not username_display:
        raise ValueError("Invalid username display")
    
    logger.info(f"Looking for user with display name: {username_display}")
    
    # Try common prefixes
    possible_usernames = [
        'r' + username_display.lower(),  # r prefix (most common)
        'u' + username_display.lower(),  # u prefix
        'a' + username_display.lower(),  # a prefix
        username_display.lower(),         # no prefix
    ]
    
    user = None
    for possible_username in possible_usernames:
        try:
            user = User.objects.get(username__iexact=possible_username)
            logger.info(f"Found user: {user.username} (ID: {user.id})")
            return user
        except User.DoesNotExist:
            continue
    
    # Last resort: search all users and check if username[1:].upper() matches
    for u in User.objects.all():
        if len(u.username) > 1 and u.username[1:].upper() == username_display:
            logger.info(f"Found user via substring match: {u.username} (ID: {u.id})")
            return u
    
    raise ValueError(f"User not found with display name: {username_display}")


def find_timerange(user_display, min_tag, kind, partial):
    """
    Find a TimeRange object based on user display name, min_tag (von), kind, and partial.
    
    Args:
        user_display: User display name "Nachname, Vorname (USERNAME)"
        min_tag: Date (string 'YYYY-MM-DD' or date object) - first visible day in week view
        kind: TimeRange kind (e.g., 'a', 'p', 'k')
        partial: Partial day indicator (empty string for full day, 'f'/'a' for half days)
    
    Returns:
        TimeRange: Found TimeRange object
    
    Raises:
        ValueError: If not found or multiple found
    """
    username_display = extract_username(user_display)
    if not username_display:
        raise ValueError(f"Could not extract username from: {user_display}")
    
    user = find_user_by_display_name(username_display)
    
    # Parse date
    if isinstance(min_tag, str):
        min_tag_date = datetime.datetime.strptime(min_tag, '%Y-%m-%d').date()
    else:
        min_tag_date = min_tag
    
    # Find TimeRange that overlaps with this date
    # MIN_TAG is the first day this entry appears in the week view,
    # but the TimeRange might have started earlier
    try:
        # Filter by user and kind, find entries that overlap with min_tag_date
        queryset = TimeRange.objects.filter(
            user=user,
            von__lte=min_tag_date,
            bis__gte=min_tag_date,
            kind=kind if kind else ''
        )
        
        logger.info(f"Found {queryset.count()} TimeRanges overlapping with {min_tag_date}")
        
        # Further filter by partial if specified
        if partial:
            # Need to check JSON field
            timeranges = []
            for tr in queryset:
                tr_partial = tr.data.get(TimeRange.DATA_PARTIAL, '') if tr.data else ''
                if tr_partial == partial:
                    timeranges.append(tr)
            
            if len(timeranges) == 0:
                raise TimeRange.DoesNotExist
            elif len(timeranges) > 1:
                raise TimeRange.MultipleObjectsReturned
            
            return timeranges[0]
        else:
            # For non-partial entries or empty entries
            for tr in queryset:
                tr_partial = tr.data.get(TimeRange.DATA_PARTIAL, '') if tr.data else ''
                if not tr_partial:
                    return tr
            
            raise TimeRange.DoesNotExist
            
    except TimeRange.DoesNotExist:
        raise ValueError(f"TimeRange not found for user={user.username}, date={min_tag_date}, kind={kind}, partial={partial}")
    except TimeRange.MultipleObjectsReturned:
        raise ValueError(f"Multiple TimeRanges found for user={user.username}, date={min_tag_date}, kind={kind}, partial={partial}")


def adjust_timerange_boundary(timerange, new_von=None, new_bis=None, auto_delete_invalid=True):
    """
    Adjust von/bis dates of a TimeRange entry.
    
    Args:
        timerange: TimeRange object to modify
        new_von: New start date (optional, keeps existing if None)
        new_bis: New end date (optional, keeps existing if None)
        auto_delete_invalid: If True, delete entry if von > bis; if False, raise ValueError
    
    Returns:
        str: 'saved' if saved successfully, 'deleted' if deleted, 'unchanged' if no changes
    """
    if new_von is not None:
        timerange.von = new_von
    if new_bis is not None:
        timerange.bis = new_bis
    
    # Check validity
    if timerange.von > timerange.bis:
        if auto_delete_invalid:
            logger.info(f"TimeRange becomes invalid ({timerange.von} > {timerange.bis}), deleting ID={timerange.id}")
            timerange.delete()
            return 'deleted'
        else:
            raise ValueError(f"Invalid TimeRange: von ({timerange.von}) > bis ({timerange.bis})")
    
    timerange.save()
    logger.info(f"Adjusted TimeRange ID={timerange.id}: {timerange.von} - {timerange.bis}")
    return 'saved'


def delete_timerange(timerange):
    """
    Delete a TimeRange with logging.
    
    Args:
        timerange: TimeRange object to delete
    """
    logger.info(f"Deleting TimeRange ID={timerange.id}: {timerange.von} - {timerange.bis}, user={timerange.user.username}, kind={timerange.kind}")
    timerange.delete()
