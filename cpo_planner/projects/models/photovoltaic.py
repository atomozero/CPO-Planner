# cpo_planner/projects/models/photovoltaic.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class PhotovoltaicSystem(models.Model):
    """
    Modello per la gestione degli impianti fotovoltaici associati alle stazioni di ricarica
    """
    charging_station = models.OneToOneField(
        'ChargingStation', 
        on_delete=models.CASCADE, 
        related_name='photovoltaic_system',
        verbose_name=_('Stazione di Ricarica')
    )
    
    # Dati tecnici
    capacity = models.DecimalField(
        _('Capacità installata'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0.1)],
        help_text=_('kWp (kilowatt picco)')
    )
    
    PANEL_TYPE_CHOICES = [
        ('monocrystalline', _('Monocristallino')),
        ('polycrystalline', _('Policristallino')),
        ('thin_film', _('Film sottile')),
        ('bifacial', _('Bifacciale')),
    ]
    panel_type = models.CharField(
        _('Tipo di pannelli'), 
        max_length=20, 
        choices=PANEL_TYPE_CHOICES, 
        default='monocrystalline'
    )
    
    total_area = models.DecimalField(
        _('Superficie totale'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0.1)],
        help_text=_('m²')
    )
    
    number_of_panels = models.PositiveIntegerField(
        _('Numero di pannelli'),
        validators=[MinValueValidator(1)]
    )
    
    # Dati di installazione
    installation_cost = models.DecimalField(
        _('Costo installazione'), 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    inverter_cost = models.DecimalField(
        _('Costo inverter'), 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    
    additional_equipment_cost = models.DecimalField(
        _('Costo equipaggiamento aggiuntivo'), 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    
    # Parametri operativi
    expected_annual_production = models.DecimalField(
        _('Produzione annuale stimata'), 
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('kWh/anno')
    )
    
    efficiency_loss_year = models.DecimalField(
        _('Perdita efficienza annuale'), 
        max_digits=4, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        default=0.5,
        help_text=_('% di perdita di efficienza per anno')
    )
    
    # Parametri economici
    incentive_percentage = models.DecimalField(
        _('Percentuale incentivi'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        help_text=_('% del costo totale coperto da incentivi')
    )
    
    energy_sale_price = models.DecimalField(
        _('Prezzo vendita energia in eccesso'), 
        max_digits=6, 
        decimal_places=4,
        validators=[MinValueValidator(0)],
        default=0,
        help_text=_('€/kWh per energia immessa in rete')
    )
    
    # Date
    installation_date = models.DateField(_('Data installazione'))
    expected_lifespan = models.PositiveIntegerField(
        _('Vita utile prevista'),
        default=25,
        help_text=_('anni')
    )
    
    def calculate_total_cost(self):
        """
        Calcola il costo totale dell'impianto fotovoltaico
        """
        return self.installation_cost + self.inverter_cost + self.additional_equipment_cost
    
    def calculate_net_cost(self):
        """
        Calcola il costo netto considerando eventuali incentivi
        """
        total_cost = self.calculate_total_cost()
        incentive_amount = total_cost * (self.incentive_percentage / 100)
        return total_cost - incentive_amount
    
    def calculate_annual_savings(self, energy_cost):
        """
        Calcola il risparmio annuale basato sul costo dell'energia
        """
        return self.expected_annual_production * energy_cost
    
    def calculate_payback_period(self, energy_cost):
        """
        Calcola il periodo di ritorno dell'investimento
        """
        annual_savings = self.calculate_annual_savings(energy_cost)
        if annual_savings > 0:
            net_cost = self.calculate_net_cost()
            return net_cost / annual_savings
        return None
    
    def __str__(self):
        return f"Impianto FV {self.capacity} kWp - {self.charging_station.name}"
    
    class Meta:
        verbose_name = _('Impianto Fotovoltaico')
        verbose_name_plural = _('Impianti Fotovoltaici')