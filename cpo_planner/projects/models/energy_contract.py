# cpo_planner/projects/models/energy_contract.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from decimal import Decimal

class EnergyContract(models.Model):
    """
    Modello per la gestione dei contratti di fornitura elettrica
    """
    name = models.CharField(_('Nome Contratto'), max_length=100)
    provider = models.CharField(_('Fornitore'), max_length=100)
    
    # Dettagli contrattuali
    contract_number = models.CharField(_('Numero Contratto'), max_length=50, blank=True, null=True)
    start_date = models.DateField(_('Data Inizio'))
    end_date = models.DateField(_('Data Fine'))
    
    # Tariffe
    TARIFF_TYPE_CHOICES = [
        ('fixed', _('Tariffa Fissa')),
        ('time_bands', _('Fasce Orarie')),
        ('peak_off_peak', _('Picco/Fuori Picco')),
        ('variable', _('Variabile')),
    ]
    tariff_type = models.CharField(_('Tipo Tariffa'), max_length=20, choices=TARIFF_TYPE_CHOICES)
    
    # Prezzi
    energy_price_kwh = models.DecimalField(
        _('Prezzo Energia (€/kWh)'), 
        max_digits=6, 
        decimal_places=4,
        validators=[MinValueValidator(0)]
    )
    
    energy_price_f1 = models.DecimalField(
        _('Prezzo F1 (€/kWh)'), 
        max_digits=6, 
        decimal_places=4,
        validators=[MinValueValidator(0)],
        null=True, blank=True,
        help_text=_('Prezzo fascia F1 (lun-ven 8-19)')
    )
    
    energy_price_f2 = models.DecimalField(
        _('Prezzo F2 (€/kWh)'), 
        max_digits=6, 
        decimal_places=4,
        validators=[MinValueValidator(0)],
        null=True, blank=True,
        help_text=_('Prezzo fascia F2 (lun-ven 7-8, 19-23, sab 7-23)')
    )
    
    energy_price_f3 = models.DecimalField(
        _('Prezzo F3 (€/kWh)'), 
        max_digits=6, 
        decimal_places=4,
        validators=[MinValueValidator(0)],
        null=True, blank=True,
        help_text=_('Prezzo fascia F3 (lun-sab 23-7, dom e festivi)')
    )
    
    # Costi fissi
    fixed_monthly_cost = models.DecimalField(
        _('Costo Fisso Mensile (€)'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0
    )
    
    power_cost_kw = models.DecimalField(
        _('Costo Potenza (€/kW/mese)'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text=_('Costo mensile per kW di potenza impegnata')
    )
    
    # Altri dettagli
    annual_adjustment = models.DecimalField(
        _('Adeguamento Annuo (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text=_('Percentuale di adeguamento annuale del prezzo')
    )
    
    max_power = models.DecimalField(
        _('Potenza Massima (kW)'), 
        max_digits=8, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_('Potenza massima contrattuale')
    )
    
    has_penalties = models.BooleanField(_('Prevede Penali'), default=False)
    penalties_description = models.TextField(_('Descrizione Penali'), blank=True, null=True)
    
    contract_file = models.FileField(_('File Contratto'), upload_to='contracts/', blank=True, null=True)
    notes = models.TextField(_('Note'), blank=True, null=True)
    
    # Projects that use this contract
    projects = models.ManyToManyField(
        'Project', 
        through='ProjectEnergyContract',
        related_name='energy_contracts',
        verbose_name=_('Progetti')
    )
    
    def get_weighted_average_price(self):
        """
        Calcola il prezzo medio ponderato in caso di tariffe a fasce
        """
        if self.tariff_type == 'fixed':
            return self.energy_price_kwh
        
        if self.tariff_type == 'time_bands' and self.energy_price_f1 and self.energy_price_f2 and self.energy_price_f3:
            # Pesi indicativi per le fasce (da personalizzare in base alle statistiche di utilizzo)
            f1_weight = Decimal('0.5')  # 50% in F1
            f2_weight = Decimal('0.3')  # 30% in F2
            f3_weight = Decimal('0.2')  # 20% in F3
            
            return (
                (self.energy_price_f1 * f1_weight) + 
                (self.energy_price_f2 * f2_weight) + 
                (self.energy_price_f3 * f3_weight)
            )
        
        return self.energy_price_kwh
    
    def calculate_monthly_cost(self, kwh_consumption, power_kw):
        """
        Calcola il costo mensile in base al consumo e alla potenza
        """
        energy_cost = kwh_consumption * self.get_weighted_average_price()
        power_cost = power_kw * self.power_cost_kw
        total_cost = energy_cost + power_cost + self.fixed_monthly_cost
        
        return {
            'energy_cost': energy_cost,
            'power_cost': power_cost,
            'fixed_cost': self.fixed_monthly_cost,
            'total_cost': total_cost
        }
    
    def is_active(self):
        """
        Verifica se il contratto è attualmente attivo
        """
        from django.utils import timezone
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date
    
    def __str__(self):
        return f"{self.name} - {self.provider}"
    
    class Meta:
        verbose_name = _('Contratto Energia')
        verbose_name_plural = _('Contratti Energia')


class ProjectEnergyContract(models.Model):
    """
    Modello di relazione tra progetti e contratti energetici
    """
    project = models.ForeignKey(
        'Project', 
        on_delete=models.CASCADE,
        verbose_name=_('Progetto')
    )
    
    energy_contract = models.ForeignKey(
        'EnergyContract', 
        on_delete=models.CASCADE,
        verbose_name=_('Contratto Energia')
    )
    
    start_date = models.DateField(_('Data Inizio Utilizzo'))
    end_date = models.DateField(_('Data Fine Utilizzo'), null=True, blank=True)
    
    notes = models.TextField(_('Note'), blank=True, null=True)
    
    def __str__(self):
        return f"{self.project.name} - {self.energy_contract.name}"
    
    class Meta:
        verbose_name = _('Associazione Progetto-Contratto')
        verbose_name_plural = _('Associazioni Progetto-Contratto')
        unique_together = ['project', 'energy_contract', 'start_date']