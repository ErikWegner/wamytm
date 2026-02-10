from django.urls import include, path

from .views import index, add, list as list_views, overlap
from .admin import korporator_admin

app_name = "wamytmapp"
urlpatterns = [
    path('', index.index, name='index'),
    path('ical/a/ou-<int:orgunit>.ics', list_views.TeamFeed(), name='icalfeed-by-orgunit'),
    path('survey', list_views.weekCSV, name='weekCSV'),
    path('add', add.add, name='add'),
    path('list', list_views.list2, name='list2'),
    path('timeranges', list_views.TimeRangesList.as_view()),
    path('check', list_views.conflict_check),
    path('getorgid', list_views.getorgid),
    path('api/resize-entry/', overlap.resize_entry, name='resize_entry'),
    path('api/undo-resize/', overlap.undo_resize, name='undo_resize'),
]
