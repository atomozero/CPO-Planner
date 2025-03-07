from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

def project_logo_path(instance, filename):
    """Path per il logo del progetto"""
    return f'project_logos/project_{instance.id}/{filename}'

class Project(models.Model):
    """Progetto principale che include piu comuni"""
    # Informazioni di base
    name = models.CharField(_("Nome Progetto"), max_length=255)
    description = models.TextField(_("Descrizione"), blank=True, null=True)
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='projects', null=True, blank=True)
    project_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    logo = models.ImageField(_("Logo Progetto"), upload_to=project_logo_path, blank=True, null=True)
    
    # Informazioni geografiche
    region = models.CharField(_("Regione"), max_length=100, default="Italia")
    
    # Timeline
    start_date = models.DateField(_("Data Inizio Progetto"), default="2023-01-01")
    expected_completion_date = models.DateField(_("Data Prevista Completamento"), default="2025-12-31")
    actual_completion_date = models.DateField(_("Data Effettiva Completamento"), null=True, blank=True)
    
    # Informazioni finanziarie
    total_budget = models.DecimalField(_("Budget Totale"), max_digits=15, decimal_places=2, default=0)
    total_expected_revenue = models.DecimalField(_("Ricavi Attesi Totali"), max_digits=15, decimal_places=2, default=0)
    total_roi = models.DecimalField(_("ROI Totale"), max_digits=10, decimal_places=2, blank=True, null=True, default=0, validators=[
        MinValueValidator(Decimal('-99.99')), 
        MaxValueValidator(Decimal('9999.99'))
    ])
    
    # Informazioni prestito
    loan_amount = models.DecimalField(_("Importo Prestito"), max_digits=12, decimal_places=2, default=0)
    loan_interest_rate = models.DecimalField(_("Tasso di Interesse"), max_digits=5, decimal_places=2, default=0)
    loan_term_years = models.PositiveIntegerField(_("Durata Prestito (anni)"), default=10)
    pre_amortization_years = models.PositiveIntegerField(_("Anni di Preammortamento"), default=0)
    
    # Stato
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('approval', _('In Approvazione')),
        ('in_progress', _('In Corso')),
        ('construction', _('In Costruzione')), 
        ('operational', _('Operativo')),
        ('maintenance', _('In Manutenzione')),
        ('completed', _('Completato')),
        ('suspended', _('Sospeso')),
        ('closed', _('Chiuso'))
    ]
    status = models.CharField(_("Stato Progetto"), max_length=20, choices=STATUS_CHOICES, default='planning')
    
    # Sostenibilita
    photovoltaic_integration = models.BooleanField(_("Integrazione Fotovoltaico"), default=False)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_total_metrics(self):
        """Calcola metriche totali del progetto basate sui sotto-progetti"""
        # Try both relationship names to handle both models
        try:
            sub_projects = self.subprojects.all()  # Usa il related_name 'subprojects' definito nel modello SubProject
        except AttributeError:
            try:
                sub_projects = self.subproject_set.all()  # Fallback al nome di relazione predefinito
            except AttributeError:
                # Se entrambi falliscono, query direttamente dal modello
                from .subproject import SubProject
                sub_projects = SubProject.objects.filter(project=self)
                
        if sub_projects:
            self.total_budget = sum(sp.budget for sp in sub_projects)
            self.total_expected_revenue = sum(sp.expected_revenue for sp in sub_projects)
            if len(sub_projects) > 0:
                self.total_roi = sum(sp.roi for sp in sub_projects) / len(sub_projects)
            self.save()
    
    def __str__(self):
        return f"{self.name} - {self.region}"
    
    class Meta:
        verbose_name = _("Progetto")
        verbose_name_plural = _("Progetti")