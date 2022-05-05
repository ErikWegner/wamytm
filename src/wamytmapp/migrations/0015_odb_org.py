# Generated by Django 4.0.3 on 2022-04-04 22:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wamytmapp', '0014_mv_odb_org_kind_mv_oms_daten_odb_mitarbeiter2strukt_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ODB_ORG',
            fields=[
                ('org_id', models.IntegerField(primary_key=True, serialize=False)),
                ('org_name', models.CharField(max_length=255, null=True)),
                ('org_kbez', models.CharField(max_length=255, null=True)),
            ],
            options={
                'db_table': 'odb_org',
            },
        ),
    ]