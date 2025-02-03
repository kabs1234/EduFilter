# Generated by Django 5.0 on 2025-02-03 05:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('script_server', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserIP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=100, unique=True)),
                ('ip_address', models.CharField(max_length=100)),
                ('port', models.IntegerField(default=8081)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
