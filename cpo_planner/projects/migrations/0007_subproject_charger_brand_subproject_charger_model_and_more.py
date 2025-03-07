# Generated by Django 4.2.9 on 2025-03-05 22:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_subproject_address_subproject_latitude_approved_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='subproject',
            name='charger_brand',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Marca Colonnina'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='charger_model',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='Modello Colonnina'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='civil_works_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Costo Opere Civili'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='connection_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Costo Allaccio Rete'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='connector_types',
            field=models.CharField(blank=True, help_text='Separati da virgola, esempio: Type 2, CCS, CHAdeMO', max_length=255, null=True, verbose_name='Tipi di Connettori'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='equipment_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Costo Colonnina'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='ground_area_sqm',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=6, null=True, verbose_name='Area Occupata (m²)'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='installation_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Costo Installazione'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='num_connectors',
            field=models.PositiveIntegerField(default=1, verbose_name='Numero Connettori'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='other_costs',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Altri Costi'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='permit_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Costo Permessi'),
        ),
        migrations.AddField(
            model_name='subproject',
            name='power_kw',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Potenza (kW)'),
        ),
        migrations.AlterField(
            model_name='subproject',
            name='budget',
            field=models.DecimalField(decimal_places=2, max_digits=12, verbose_name='Budget Totale'),
        ),
    ]
