# Generated by Django 3.0.4 on 2020-04-13 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wamytmapp', '0004_timerange_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='orgunit',
            options={'ordering': ['name'], 'verbose_name': 'Organizational unit', 'verbose_name_plural': 'Organizational units'},
        ),
        migrations.AddIndex(
            model_name='alldayevent',
            index=models.Index(fields=['day'], name='wamytmapp_a_day_12b20a_idx'),
        ),
        migrations.AddIndex(
            model_name='timerange',
            index=models.Index(fields=['start', 'end'], name='wamytmapp_t_start_60363a_idx'),
        ),
    ]
