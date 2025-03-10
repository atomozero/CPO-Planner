# Generated by Django 4.2.9 on 2025-03-06 07:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0007_globalsettings'),
    ]

    operations = [
        migrations.AddField(
            model_name='electricitytariff',
            name='pun_fee_f1',
            field=models.DecimalField(decimal_places=4, default=0.02, help_text='Costo aggiuntivo rispetto al PUN per fascia F1', max_digits=6, verbose_name='Spread su PUN F1 (€/kWh)'),
        ),
        migrations.AddField(
            model_name='electricitytariff',
            name='pun_fee_f2',
            field=models.DecimalField(decimal_places=4, default=0.02, help_text='Costo aggiuntivo rispetto al PUN per fascia F2', max_digits=6, verbose_name='Spread su PUN F2 (€/kWh)'),
        ),
        migrations.AddField(
            model_name='electricitytariff',
            name='pun_fee_f3',
            field=models.DecimalField(decimal_places=4, default=0.02, help_text='Costo aggiuntivo rispetto al PUN per fascia F3', max_digits=6, verbose_name='Spread su PUN F3 (€/kWh)'),
        ),
        migrations.AddField(
            model_name='electricitytariff',
            name='tariff_type',
            field=models.CharField(choices=[('fixed', 'Prezzo Fisso'), ('pun', 'Indicizzato PUN')], default='fixed', max_length=10, verbose_name='Tipo di tariffa'),
        ),
        migrations.CreateModel(
            name='PunData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(verbose_name='Data')),
                ('hour', models.IntegerField(choices=[(0, '00:00'), (1, '01:00'), (2, '02:00'), (3, '03:00'), (4, '04:00'), (5, '05:00'), (6, '06:00'), (7, '07:00'), (8, '08:00'), (9, '09:00'), (10, '10:00'), (11, '11:00'), (12, '12:00'), (13, '13:00'), (14, '14:00'), (15, '15:00'), (16, '16:00'), (17, '17:00'), (18, '18:00'), (19, '19:00'), (20, '20:00'), (21, '21:00'), (22, '22:00'), (23, '23:00')], verbose_name='Ora')),
                ('price', models.DecimalField(decimal_places=4, max_digits=8, verbose_name='Prezzo (€/MWh)')),
                ('zone', models.CharField(default='NORD', max_length=10, verbose_name='Zona di mercato')),
                ('timeband', models.CharField(choices=[('F1', 'F1 - Ore di punta'), ('F2', 'F2 - Ore intermedie'), ('F3', 'F3 - Ore fuori punta')], max_length=2, verbose_name='Fascia oraria')),
            ],
            options={
                'verbose_name': 'Dato PUN',
                'verbose_name_plural': 'Dati PUN',
                'ordering': ['-date', 'hour'],
                'unique_together': {('date', 'hour', 'zone')},
            },
        ),
        migrations.CreateModel(
            name='EnergyPriceProjection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Data creazione')),
                ('year', models.IntegerField(verbose_name='Anno di riferimento')),
                ('month', models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12)], verbose_name='Mese di riferimento')),
                ('f1_price', models.DecimalField(decimal_places=4, max_digits=6, verbose_name='Prezzo medio F1 (€/kWh)')),
                ('f2_price', models.DecimalField(decimal_places=4, max_digits=6, verbose_name='Prezzo medio F2 (€/kWh)')),
                ('f3_price', models.DecimalField(decimal_places=4, max_digits=6, verbose_name='Prezzo medio F3 (€/kWh)')),
                ('avg_price', models.DecimalField(decimal_places=4, max_digits=6, verbose_name='Prezzo medio (€/kWh)')),
                ('inflation_rate', models.DecimalField(decimal_places=2, max_digits=5, verbose_name='Tasso inflazione applicato (%)')),
                ('base_period_start', models.DateField(verbose_name='Inizio periodo base')),
                ('base_period_end', models.DateField(verbose_name='Fine periodo base')),
                ('notes', models.TextField(blank=True, verbose_name='Note')),
            ],
            options={
                'verbose_name': 'Proiezione prezzi energia',
                'verbose_name_plural': 'Proiezioni prezzi energia',
                'ordering': ['-year', '-month'],
                'unique_together': {('year', 'month')},
            },
        ),
    ]
