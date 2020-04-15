import django.contrib.postgres.fields.jsonb
import django.core.serializers.json
from django.db import migrations

def remove_subkind(apps, schema_editor):
    key = 'kinddetail'
    TimeRange = apps.get_model('wamytmapp', 'TimeRange')
    for timerange in TimeRange.objects.all():
        if timerange.data is None or key not in timerange.data:
            continue
        del(timerange.data[key])
        timerange.save()

class Migration(migrations.Migration):

    dependencies = [
        ('wamytmapp', '0005_indexes'),
    ]

    operations = [
        migrations.RunPython(remove_subkind),
    ]
