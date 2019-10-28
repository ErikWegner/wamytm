from django.http import HttpResponse
from django.template import loader

from .models import TimeRange

def index(request):
    timeranges_thisweek = TimeRange.objects.thisWeek()
    template = loader.get_template('wamytmapp/index.html')
    context = {
        'this_week': timeranges_thisweek,
    }
    return HttpResponse(template.render(context, request))
