# Generated by Django 4.2.9 on 2025-03-07 12:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0011_municipality_logo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='municipality',
            name='province',
            field=models.CharField(max_length=100, verbose_name='Provincia'),
        ),
    ]
