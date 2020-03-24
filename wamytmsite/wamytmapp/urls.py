from django.urls import include, path

from . import views
from .admin import korporator_admin

app_name = "wamytmapp"
urlpatterns = [
    path('', views.index, name='index'),
    path('ical/a/ou-<int:orgunit>.ics', views.TeamFeed(), name='icalfeed-by-orgunit'),
    path('survey', views.weekCSV, name='weekCSV'),
    path('add', views.add, name='add'),
    path('list', views.list1, name='list1'),
    path('profile', views.profile, name="profile"),
    path('timeranges', views.TimeRangesList.as_view())
]
