# Generated by Django 5.0 on 2025-02-26 04:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('script_server', '0004_alter_usersettings_blocked_sites_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userstatus',
            name='user_id',
            field=models.CharField(max_length=100, unique=True),
        ),
    ]
