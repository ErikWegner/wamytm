# Generated by Django 4.2.2 on 2023-06-30 12:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wamytmapp', '0028_rename_vt_id_ma2vt_vt'),
    ]

    operations = [
        migrations.AddField(
            model_name='virtualteam',
            name='is_privat',
            field=models.BooleanField(default=False),
        ),
    ]
