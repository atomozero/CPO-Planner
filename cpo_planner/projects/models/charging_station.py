# cpo_planner/projects/models/charging_station.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class ChargingStation(models.Model):
    """
    Modello per la gestione delle singole stazioni di ricarica
    """
    sub_project = models.ForeignKey('SubProject', on_delete=models.CASCADE, verbose_name=_('Sotto-Progetto'))
    
    # Identificazione e Localizzazione
    name = models.CharField(_('Nome Stazione'), max_length=100)
    identifier = models.CharField(_('Identificatore Stazione'), max_length=50, unique=True)
    address = models.CharField(_('Indirizzo'), max_length=255)
    latitude = models.DecimalField(_('Latitudine'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_('Longitudine'), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Dettagli Tecnici
    POWER_TYPE_CHOICES = [
        ('ac', _('AC')),
        ('dc', _('DC')),
        ('ac_dc', _('AC/DC')),
    ]
    power_type = models.CharField(_('Tipo di Potenza'), max_length=10, choices=POWER_TYPE_CHOICES, default='ac')
    charging_points = models.PositiveIntegerField(_('Punti di Ricarica'), default=1)
    total_power = models.DecimalField(_('Potenza Totale'), max_digits=8, decimal_places=2, help_text='kW')
    
    # Costi
    station_cost = models.DecimalField(_('Costo Colonnina'), max_digits=10, decimal_places=2)
    installation_cost = models.DecimalField(_('Costo Installazione'), max_digits=10, decimal_places=2)
    connection_cost = models.DecimalField(_('Costo Allaccio'), max_digits=10, decimal_places=2)
    design_cost = models.DecimalField(_('Costo Progettazione'), max_digits=10, decimal_places=2, default=0)
    permit_cost = models.DecimalField(_('Costo Permessi'), max_digits=10, decimal_places=2, default=0)
    
    # Parametri operativi
    energy_cost_kwh = models.DecimalField(_('Costo Energia (€/kWh)'), max_digits=6, decimal_places=4)
    charging_price_kwh = models.DecimalField(_('Prezzo Ricarica (€/kWh)'), max_digits=6, decimal_places=4)
    estimated_sessions_day = models.DecimalField(_('Sessioni Stimate/Giorno'), max_digits=6, decimal_places=2)
    avg_kwh_session = models.DecimalField(_('Media kWh/Sessione'), max_digits=6, decimal_places=2)
    
    # Date
    installation_date = models.DateField(_('Data Installazione'), null=True, blank=True)
    
    # Stato e Manutenzione
    STATUS_CHOICES = [
        ('planned', _('Pianificata')),
        ('active', _('Attiva')),
        ('maintenance', _('Manutenzione')),
        ('inactive', _('Inattiva'))
    ]
    status = models.CharField(_('Stato Stazione'), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Impianto Fotovoltaico
    has_photovoltaic_system = models.BooleanField(_('Impianto Fotovoltaico'), default=False)
    photovoltaic_capacity = models.DecimalField(_('Capacità Fotovoltaico'), max_digits=8, decimal_places=2, null=True, blank=True, help_text='kWp')
    
    def calculate_annual_metrics(self):
        """
        Calcola metriche annuali basate sui dati della stazione
        """
        daily_revenue = self.charging_price_kwh * self.avg_kwh_session * self.estimated_sessions_day
        annual_revenue = daily_revenue * 365
        annual_costs = self.calculate_annual_operational_costs()
        annual_profit = annual_revenue - annual_costs
        return {
            'annual_revenue': annual_revenue,
            'annual_costs': annual_costs,
            'annual_profit': annual_profit
        }
    
    def calculate_annual_operational_costs(self):
        """
        Calcola i costi operativi annuali stimati
        """
        # Costo energia
        daily_energy_cost = self.energy_cost_kwh * self.avg_kwh_session * self.estimated_sessions_day
        annual_energy_cost = daily_energy_cost * 365
        
        # Costo manutenzione (assumiamo 5% del costo della stazione)
        annual_maintenance_cost = self.station_cost * Decimal('0.05')
        
        # Totale costi operativi
        return annual_energy_cost + annual_maintenance_cost
    
    def calculate_total_investment(self):
        """
        Calcola l'investimento totale per questa stazione
        """
        return self.station_cost + self.installation_cost + self.connection_cost + self.design_cost + self.permit_cost
    
    def __str__(self):
        return f"{self.name} ({self.identifier})"
    
    class Meta:
        verbose_name = _('Stazione di Ricarica')
        verbose_name_plural = _('Stazioni di Ricarica')