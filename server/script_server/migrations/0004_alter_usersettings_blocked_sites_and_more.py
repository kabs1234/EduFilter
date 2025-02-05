# Generated by Django 5.0 on 2025-02-06 11:00

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('script_server', '0003_usersettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersettings',
            name='blocked_sites',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='categories',
            field=models.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='usersettings',
            name='excluded_sites',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.TextField(), default=list, size=None),
        ),
    ]
