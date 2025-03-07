# Generated by Django 4.2.9 on 2025-03-06 22:57

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('cpo_core', '0007_alter_charger_options_charger_charging_station_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subproject',
            name='status_changed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='status_changes', to=settings.AUTH_USER_MODEL, verbose_name='Cambio Stato Da'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='status_changed_date',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Data Cambio Stato'),
        ),
    ]
