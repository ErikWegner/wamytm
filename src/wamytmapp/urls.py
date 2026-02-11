from django.urls import include, path

from .views import index, add, list as list_views, overlap
from .admin import korporator_admin

app_name = "wamytmapp"
urlpatterns = [
    path('', index.index, name='index'),
    path('info', index.info, name='info'),
    path('ical/a/ou-<int:orgunit>.ics', list_views.TeamFeed(), name='icalfeed-by-orgunit'),
    path('survey', list_views.weekCSV, name='weekCSV'),
    path('add', add.add, name='add'),
    path('list', list_views.list2, name='list2'),
    path('timeranges', list_views.TimeRangesList.as_view()),
    path('check', list_views.conflict_check),
    path('getorgid', list_views.getorgid),
    path('api/resize-entry/', overlap.resize_entry, name='resize_entry'),
    path('api/undo-resize/', overlap.undo_resize, name='undo_resize'),
    path('api/change-type-visible/', overlap.change_type_visible, name='change_type_visible'),
    path('api/undo-change-type/', overlap.undo_change_type, name='undo_change_type'),
    path('api/add-entry-at-day/', overlap.add_entry_at_day, name='add_entry_at_day'),
    path('api/undo-add-entry/', overlap.undo_add_entry, name='undo_add_entry'),
]
