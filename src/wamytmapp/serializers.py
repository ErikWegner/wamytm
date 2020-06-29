from rest_framework import serializers

from .models import TimeRange

class TimeRangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeRange
        fields = ['user', 'orgunit', 'start', 'end', 'kind']
