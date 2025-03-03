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
    identifier = models.CharField(_('Identificatore Stazione'), max_length=50, unique=True)
    address = models.CharField(_('Indirizzo'), max_length=255)
    latitude = models.DecimalField(_('Latitudine'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_('Longitudine'), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Dettagli Tecnici
    charging_type = models.CharField(_('Tipo di Ricarica'), max_length=50)
    max_power = models.DecimalField(_('Potenza Massima'), max_digits=6, decimal_places=2, help_text='kW')
    
    # Costi Specifici
    installation_cost = models.DecimalField(_('Costo Installazione'), max_digits=10, decimal_places=2)
    connection_cost = models.DecimalField(_('Costo Allaccio'), max_digits=10, decimal_places=2)
    estimated_monthly_revenue = models.DecimalField(_('Ricavi Mensili Stimati'), max_digits=10, decimal_places=2)
    
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
        annual_revenue = self.estimated_monthly_revenue * 12
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
        # TODO: Implementare logica dettagliata di calcolo dei costi
        return Decimal('0.00')
    
    def __str__(self):
        return f"{self.identifier} - {self.address}"
    
    class Meta:
        verbose_name = _('Stazione di Ricarica')
        verbose_name_plural = _('Stazioni di Ricarica')
