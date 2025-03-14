# Generated by Django 4.2.9 on 2025-03-07 13:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cpo_core', '0010_municipality_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='municipality',
            name='latitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Latitudine'),
        ),
        migrations.AddField(
            model_name='municipality',
            name='longitude',
            field=models.FloatField(blank=True, null=True, verbose_name='Longitudine'),
        ),
    ]
