# Generated by Django 4.0.6 on 2022-12-01 09:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wamytmapp', '0027_alter_ma2vt_user_alter_virtualteam_vt_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ma2vt',
            old_name='vt_id',
            new_name='vt',
        ),
    ]