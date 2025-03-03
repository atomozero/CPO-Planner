# environmental/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Avg, F
from cpo_planner.projects.models.project import Project
from cpo_planner.projects.models.municipality import Municipality
from cpo_planner.projects.models.charging_station import ChargingStation

class EmissionFactor(models.Model):
    """Fattori di emissione per diverse fonti di energia"""
    
    class EnergySourceType(models.TextChoices):
        ELECTRICITY_MIX = 'electricity_mix', _('Mix Elettrico Nazionale')
        RENEWABLE = 'renewable', _('Energia Rinnovabile')
        GASOLINE = 'gasoline', _('Benzina')
        DIESEL = 'diesel', _('Diesel')
        NATURAL_GAS = 'natural_gas', _('Gas Naturale')
        LPG = 'lpg', _('GPL')
        HYDROGEN = 'hydrogen', _('Idrogeno')
        
    name = models.CharField(_('Nome'), max_length=100)
    source_type = models.CharField(
        _('Tipo Fonte'),
        max_length=20,
        choices=EnergySourceType.choices,
        default=EnergySourceType.ELECTRICITY_MIX
    )
    emission_factor = models.FloatField(
        _('Fattore di Emissione (gCO2/kWh)'),
        help_text=_('Grammi di CO2 equivalenti per kWh')
    )
    year = models.IntegerField(_('Anno di Riferimento'))
    country = models.CharField(_('Paese'), max_length=100, default='Italia')
    source = models.CharField(_('Fonte Dati'), max_length=255, blank=True)
    notes = models.TextField(_('Note'), blank=True)
    is_default = models.BooleanField(_('Default per il tipo'), default=False)
    
    # Metadati e tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_emission_factors',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Fattore di Emissione')
        verbose_name_plural = _('Fattori di Emissione')
        ordering = ['-year', 'source_type']
        constraints = [
            models.UniqueConstraint(
                fields=['source_type', 'year', 'country', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_emission_factor'
            )
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()}, {self.year})"
    
    def save(self, *args, **kwargs):
        # Se questo fattore è impostato come default, rimuovi il flag dagli altri
        if self.is_default:
            EmissionFactor.objects.filter(
                source_type=self.source_type,
                year=self.year,
                country=self.country,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
            
        super().save(*args, **kwargs)

class VehicleType(models.Model):
    """Tipologie di veicoli elettrici"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    avg_consumption = models.FloatField(
        _('Consumo Medio (kWh/100km)'),
        help_text=_('kWh per 100 km di percorrenza')
    )
    avg_ice_consumption = models.FloatField(
        _('Consumo Medio Equivalente (L/100km)'),
        help_text=_('Litri per 100 km di percorrenza di un veicolo a combustione interna equivalente')
    )
    fuel_type = models.CharField(
        _('Tipo Carburante Equivalente'),
        max_length=20,
        choices=EmissionFactor.EnergySourceType.choices,
        default=EmissionFactor.EnergySourceType.GASOLINE
    )
    battery_capacity = models.FloatField(
        _('Capacità Batteria (kWh)'),
        blank=True, 
        null=True
    )
    avg_range = models.FloatField(
        _('Autonomia Media (km)'),
        blank=True, 
        null=True
    )
    
    # Percentuale della flotta
    market_share = models.FloatField(
        _('Quota di Mercato (%)'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        help_text=_('Percentuale stimata nella flotta di veicoli elettrici')
    )
    
    # Metadati e tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_vehicle_types',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Tipo Veicolo')
        verbose_name_plural = _('Tipi Veicolo')
        ordering = ['-market_share', 'name']
        
    def __str__(self):
        return self.name
    
    @property
    def energy_efficiency(self):
        """Efficienza energetica in km/kWh"""
        return 100 / self.avg_consumption if self.avg_consumption else 0

class EnvironmentalAnalysis(models.Model):
    """Analisi dell'impatto ambientale"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    
    # Entità collegata (opzionale)
    content_type = models.ForeignKey(
        'contenttypes.ContentType', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        verbose_name=_('Tipo Entità')
    )
    object_id = models.PositiveIntegerField(
        _('ID Oggetto'), 
        null=True, 
        blank=True
    )
    
    # Parametri dell'analisi
    start_date = models.DateField(_('Data Inizio'), default=timezone.now)
    end_date = models.DateField(_('Data Fine'), blank=True, null=True)
    years_projection = models.PositiveIntegerField(
        _('Anni di Proiezione'),
        default=10,
        help_text=_('Numero di anni per cui proiettare l\'impatto')
    )
    
    # Fattori di emissione utilizzati
    electricity_emission_factor = models.ForeignKey(
        EmissionFactor,
        on_delete=models.PROTECT,
        related_name='electricity_analyses',
        verbose_name=_('Fattore Emissione Elettricità'),
        limit_choices_to={'source_type': EmissionFactor.EnergySourceType.ELECTRICITY_MIX}
    )
    
    fuel_emission_factor = models.ForeignKey(
        EmissionFactor,
        on_delete=models.PROTECT,
        related_name='fuel_analyses',
        verbose_name=_('Fattore Emissione Carburante'),
        limit_choices_to={'source_type__in': [
            EmissionFactor.EnergySourceType.GASOLINE,
            EmissionFactor.EnergySourceType.DIESEL
        ]}
    )
    
    # Percentuale di energia rinnovabile
    renewable_percentage = models.FloatField(
        _('Percentuale Energia Rinnovabile'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        help_text=_('Percentuale di energia da fonti rinnovabili')
    )
    
    # Utilizzo stimato
    avg_sessions_per_day = models.FloatField(
        _('Sessioni Medie Giornaliere per Punto'),
        default=5.0,
        help_text=_('Numero medio di sessioni di ricarica al giorno per punto di ricarica')
    )
    
    avg_kwh_per_session = models.FloatField(
        _('kWh Medi per Sessione'),
        default=15.0,
        help_text=_('Energia media erogata per sessione di ricarica')
    )
    
    utilization_rate = models.FloatField(
        _('Tasso di Utilizzo (%)'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=50.0,
        help_text=_('Percentuale di utilizzo delle stazioni rispetto alla capacità massima')
    )
    
    # Risultati dell'analisi
    total_energy_delivered = models.FloatField(
        _('Energia Totale Erogata (MWh)'),
        null=True, blank=True
    )
    
    total_co2_emissions = models.FloatField(
        _('Emissioni CO2 Totali (tonnellate)'),
        null=True, blank=True
    )
    
    total_co2_saved = models.FloatField(
        _('CO2 Risparmiata Totale (tonnellate)'),
        null=True, blank=True
    )
    
    equivalent_trees = models.PositiveIntegerField(
        _('Alberi Equivalenti'),
        null=True, blank=True,
        help_text=_('Numero di alberi necessari per assorbire la stessa quantità di CO2')
    )
    
    equivalent_ice_km = models.FloatField(
        _('Km Equivalenti Veicoli ICE'),
        null=True, blank=True,
        help_text=_('Chilometri equivalenti non percorsi da veicoli a combustione interna')
    )
    
    # Metadati e tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_environmental_analyses',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Analisi Ambientale')
        verbose_name_plural = _('Analisi Ambientali')
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    
    @property
    def entity_name(self):
        """Restituisce il nome dell'entità collegata"""
        if self.content_type and self.object_id:
            try:
                return str(self.content_type.get_object_for_this_type(id=self.object_id))
            except:
                return _("Entità non trovata")
        return ""
    
    def calculate(self):
        """Calcola l'impatto ambientale"""
        from .services import EnvironmentalCalculator
        calculator = EnvironmentalCalculator(self)
        return calculator.calculate()
    
    def get_yearly_data(self):
        """Restituisce i dati annuali per grafici"""
        return self.yearly_data.order_by('year').values('year', 'energy_delivered', 'co2_emissions', 'co2_saved')

class YearlyEnvironmentalData(models.Model):
    """Dati ambientali annuali"""
    analysis = models.ForeignKey(
        EnvironmentalAnalysis,
        on_delete=models.CASCADE,
        related_name='yearly_data',
        verbose_name=_('Analisi')
    )
    year = models.PositiveIntegerField(_('Anno'))
    
    # Dati annuali
    energy_delivered = models.FloatField(_('Energia Erogata (MWh)'))
    co2_emissions = models.FloatField(_('Emissioni CO2 (tonnellate)'))
    co2_saved = models.FloatField(_('CO2 Risparmiata (tonnellate)'))
    
    # Distribuzione per tipologia di veicolo
    vehicle_distribution = models.JSONField(
        _('Distribuzione Veicoli'),
        default=dict,
        help_text=_('Distribuzione dell\'utilizzo per tipo di veicolo')
    )
    
    class Meta:
        verbose_name = _('Dato Ambientale Annuale')
        verbose_name_plural = _('Dati Ambientali Annuali')
        ordering = ['analysis', 'year']
        unique_together = ['analysis', 'year']
        
    def __str__(self):
        return f"{self.analysis.name} - {self.year}"
