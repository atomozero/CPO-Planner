# cpo_planner/projects/models/subproject.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class SubProject(models.Model):
    """
    Modello per la gestione dei sotto-progetti (per comune o zona specifica)
    """
    project = models.ForeignKey('Project', on_delete=models.CASCADE, verbose_name=_('Progetto Principale'))
    municipality = models.ForeignKey('Municipality', on_delete=models.CASCADE, verbose_name=_('Comune'))
    
    name = models.CharField(_('Nome Sotto-Progetto'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True, null=True)
    
    # Date specifiche del sotto-progetto
    start_date = models.DateField(_('Data Inizio'))
    expected_completion_date = models.DateField(_('Data Prevista Completamento'))
    
    # Informazioni Finanziarie
    budget = models.DecimalField(_('Budget'), max_digits=12, decimal_places=2)
    expected_revenue = models.DecimalField(_('Ricavi Attesi'), max_digits=12, decimal_places=2)
    roi = models.DecimalField(_('ROI'), max_digits=10, decimal_places=2, validators=[
        MinValueValidator(Decimal('-99.99')), 
        MaxValueValidator(Decimal('9999.99'))
    ])
    
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
    
    class Meta:
        verbose_name = _('Sotto-Progetto')
        verbose_name_plural = _('Sotto-Progetti')
