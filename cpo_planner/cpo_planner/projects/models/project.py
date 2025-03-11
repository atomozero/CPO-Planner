# cpo_planner/projects/models/project.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class Project(models.Model):
    """
    Modello principale per la gestione di un progetto complessivo di infrastrutture di ricarica
    """
    name = models.CharField(_('Nome Progetto'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True, null=True)
    
    # Informazioni geografiche
    region = models.CharField(_('Comune/Regione'), max_length=100)
    
    # Date di progetto
    start_date = models.DateField(_('Data Inizio Progetto'))
    expected_completion_date = models.DateField(_('Data Prevista Completamento'))
    
    # Informazioni Finanziarie Complessive
    total_budget = models.DecimalField(_('Budget Totale'), max_digits=15, decimal_places=2, default=0)
    total_expected_revenue = models.DecimalField(_('Ricavi Attesi Totali'), max_digits=15, decimal_places=2, default=0)
    total_roi = models.DecimalField(_('ROI Totale'), max_digits=10, decimal_places=2, blank=True, null=True, default=0, validators=[
        MinValueValidator(Decimal('-99.99')), 
        MaxValueValidator(Decimal('9999.99'))
    ])
    
    # Stato del Progetto
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('in_progress', _('In Corso')),
        ('completed', _('Completato')),
        ('suspended', _('Sospeso'))
    ]
    status = models.CharField(_('Stato Progetto'), max_length=20, choices=STATUS_CHOICES, default='planning')
    
    # Sostenibilità
    photovoltaic_integration = models.BooleanField(_('Integrazione Fotovoltaico'), default=False)
    
    def calculate_total_metrics(self):
        """
        Calcola metriche totali del progetto basate sui sotto-progetti
        """
        from .subproject import SubProject  # Importazione locale per evitare circolarità
        sub_projects = self.subproject_set.all()
        if sub_projects:
            self.total_budget = sum(sp.budget for sp in sub_projects)
            self.total_expected_revenue = sum(sp.expected_revenue for sp in sub_projects)
            self.total_roi = sum(sp.roi for sp in sub_projects) / len(sub_projects)
            self.save()
    
    def __str__(self):
        return f"{self.name} - {self.region}"
    
    class Meta:
        verbose_name = _('Progetto')
        verbose_name_plural = _('Progetti')
