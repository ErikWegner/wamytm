# Generated by Django 4.0.3 on 2022-04-04 22:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('wamytmapp', '0015_odb_org'),
    ]

    operations = [
        migrations.RunSQL("INSERT INTO wamytmapp_kind (kind,wertung) VALUES ('a',1); INSERT INTO wamytmapp_kind (kind,wertung) VALUES ('m',2); INSERT INTO wamytmapp_kind (kind,wertung) VALUES ('p',3);","delete from wamytmapp_kind")
    ]
