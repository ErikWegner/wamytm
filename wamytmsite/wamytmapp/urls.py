from django.urls import path

from . import views

app_name = "wamytmapp"
urlpatterns = [
    path('', views.index, name='index'),
    path('add', views.add, name='add'),
    path('list', views.list1, name='list1'),
    path('profile', views.profile, name="profile")
]
