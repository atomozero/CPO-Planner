# cpo_planner/projects/models/subproject.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class SubProject(models.Model):
    """
    Modello per la gestione delle stazioni di ricarica
    """
    project = models.ForeignKey('Project', on_delete=models.CASCADE, verbose_name=_('Progetto Principale'))
    municipality = models.ForeignKey('Municipality', on_delete=models.CASCADE, verbose_name=_('Comune'))
    
    name = models.CharField(_('Nome Stazione'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True, null=True)
    
    # Indirizzo e coordinate
    address = models.CharField(_('Indirizzo'), max_length=255, blank=True, null=True)
    latitude_proposed = models.DecimalField(_('Latitudine Proposta'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_proposed = models.DecimalField(_('Longitudine Proposta'), max_digits=9, decimal_places=6, null=True, blank=True)
    latitude_approved = models.DecimalField(_('Latitudine Approvata'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_approved = models.DecimalField(_('Longitudine Approvata'), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Specifiche tecniche della colonnina
    charger_brand = models.CharField(_('Marca Colonnina'), max_length=100, blank=True, null=True)
    charger_model = models.CharField(_('Modello Colonnina'), max_length=100, blank=True, null=True)
    power_kw = models.DecimalField(_('Potenza (kW)'), max_digits=8, decimal_places=2, null=True, blank=True)
    connector_types = models.CharField(_('Tipi di Connettori'), max_length=255, blank=True, null=True, 
                                      help_text=_('Separati da virgola, esempio: Type 2, CCS, CHAdeMO'))
    num_connectors = models.PositiveIntegerField(_('Numero Connettori'), default=1)
    ground_area_sqm = models.DecimalField(_('Area Occupata (m²)'), max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Date specifiche della stazione
    start_date = models.DateField(_('Data Inizio'))
    expected_completion_date = models.DateField(_('Data Prevista Completamento'))
    
    # Giorni di indisponibilità
    WEEKDAY_CHOICES = [
        ('', _('-- Nessuno --')),
        ('monday', _('Lunedì')),
        ('tuesday', _('Martedì')),
        ('wednesday', _('Mercoledì')),
        ('thursday', _('Giovedì')),
        ('friday', _('Venerdì')),
        ('saturday', _('Sabato')),
        ('sunday', _('Domenica')),
    ]
    weekly_market_day = models.CharField(_('Giorno Mercato Settimanale'), max_length=10, 
                                         choices=WEEKDAY_CHOICES, blank=True, null=True)
    local_festival_days = models.PositiveSmallIntegerField(_('Giorni Festa Locale/Anno'), default=0)
    rainy_days = models.PositiveSmallIntegerField(_('Giorni di Pioggia Previsti/Anno'), default=0,
                                                 help_text=_('Giorni di pioggia stimati che riducono l\'utilizzo delle colonnine'))
    
    # Informazioni Finanziarie
    budget = models.DecimalField(_('Budget Totale'), max_digits=12, decimal_places=2)
    expected_revenue = models.DecimalField(_('Ricavi Attesi'), max_digits=12, decimal_places=2)
    roi = models.DecimalField(_('ROI'), max_digits=10, decimal_places=2, default=0, validators=[
        MinValueValidator(Decimal('-99.99')), 
        MaxValueValidator(Decimal('9999.99'))
    ])
    
    # Dettaglio costi
    equipment_cost = models.DecimalField(_('Costo Colonnina'), max_digits=10, decimal_places=2, null=True, blank=True)
    installation_cost = models.DecimalField(_('Costo Installazione'), max_digits=10, decimal_places=2, null=True, blank=True)
    connection_cost = models.DecimalField(_('Costo Allaccio Rete'), max_digits=10, decimal_places=2, null=True, blank=True)
    permit_cost = models.DecimalField(_('Costo Permessi'), max_digits=10, decimal_places=2, null=True, blank=True)
    civil_works_cost = models.DecimalField(_('Costo Opere Civili'), max_digits=10, decimal_places=2, null=True, blank=True)
    other_costs = models.DecimalField(_('Altri Costi'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stato del Sotto-Progetto
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('in_progress', _('In Corso')),
        ('completed', _('Completato')),
        ('suspended', _('Sospeso'))
    ]
    status = models.CharField(_('Stato Sotto-Progetto'), max_length=20, choices=STATUS_CHOICES, default='planning')
    
    def __str__(self):
        return f"{self.name} - {self.municipality}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Aggiorna le metriche del progetto principale dopo il salvataggio
        self.project.calculate_total_metrics()
    
    def calculate_availability_factor(self):
        """
        Calcola il fattore di disponibilità basato sui giorni di indisponibilità
        """
        # Giorni totali in un anno
        total_days = 365
        
        # Calcola i giorni di indisponibilità totali
        unavailable_days = 0
        
        # Aggiungi i giorni di mercato (52 settimane)
        if self.weekly_market_day:
            unavailable_days += 52
            
        # Aggiungi i giorni di festa locale
        unavailable_days += self.local_festival_days
        
        # Calcolo della disponibilità di base
        available_days = total_days - unavailable_days
        base_availability_factor = available_days / total_days if total_days > 0 else 1.0
        
        # Calcolo dell'impatto dei giorni di pioggia (riduzione del 30%)
        rainy_days_impact = (self.rainy_days * 0.3) / total_days if total_days > 0 else 0
        
        # Fattore di disponibilità finale considerando anche i giorni di pioggia
        availability_factor = base_availability_factor * (1 - rainy_days_impact)
        
        return availability_factor
    
    class Meta:
        verbose_name = _('Sotto-Progetto')
        verbose_name_plural = _('Sotto-Progetti')