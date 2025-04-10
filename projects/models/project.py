# projects/models/project.py
from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

def project_logo_path(instance, filename):
    """Path per il logo del progetto"""
    return f'project_logos/project_{instance.id}/{filename}'

class Project(models.Model):
    """Progetto principale che include più comuni"""
    # Informazioni di base
    name = models.CharField(_("Nome Progetto"), max_length=255)
    description = models.TextField(_("Descrizione"), blank=True, null=True)
    organization = models.ForeignKey('cpo_core.Organization', on_delete=models.CASCADE, 
                                related_name='projects_app_projects', null=True, blank=True)
    project_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, 
                                    related_name='projects_app_managed_projects')
    logo = models.ImageField(_("Logo Progetto"), upload_to=project_logo_path, blank=True, null=True)
    
    # Informazioni geografiche
    region = models.CharField(_("Regione"), max_length=100, default="Italia")
    # Riferimento al comune principale
    municipality = models.ForeignKey('infrastructure.Municipality', on_delete=models.SET_NULL, 
                                   verbose_name=_("Comune principale"), 
                                   null=True, blank=True,
                                   related_name="project_app_projects")
    
    # Timeline
    start_date = models.DateField(_("Data Inizio Progetto"), null=True, blank=True)
    expected_completion_date = models.DateField(_("Data Prevista Completamento"), null=True, blank=True)
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
        from projects.models.subproject import SubProject
        
        sub_projects = SubProject.objects.filter(project=self)
                
        if sub_projects:
            self.total_budget = sum(sp.budget for sp in sub_projects)
            self.total_expected_revenue = sum(sp.expected_revenue for sp in sub_projects)
            if len(sub_projects) > 0:
                self.total_roi = sum(sp.roi for sp in sub_projects) / len(sub_projects)
            self.save(update_fields=['total_budget', 'total_expected_revenue', 'total_roi'])
    
    def sync_municipalities(self):
        """Sincronizza il comune di tutti i sottoprogetti con quello del progetto principale"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.municipality:
            logger.warning(f"Impossibile sincronizzare i comuni: nessun comune impostato per il progetto {self.id}")
            return False
        
        # Aggiorna tutti i sottoprogetti associati
        from projects.models.subproject import SubProject
        
        # Log informazioni di debug
        logger.debug(f"Aggiornamento sottoprogetti per progetto {self.id} al comune {self.municipality.id} ({self.municipality.name})")
        
        try:
            # Aggiorna il campo municipality in tutti i sottoprogetti con un singolo update
            updated = SubProject.objects.filter(project=self).update(municipality=self.municipality)
            
            logger.debug(f"Aggiornati {updated} sottoprogetti al comune {self.municipality.id}")
            
            return updated > 0
        except Exception as e:
            logger.error(f"Errore durante la sincronizzazione dei comuni: {e}")
            return False
    
    def save(self, *args, **kwargs):
        # Tieni traccia se il municipio è cambiato
        municipality_changed = False
        if self.pk:
            try:
                old_instance = Project.objects.get(pk=self.pk)
                old_municipality_id = getattr(old_instance.municipality, 'id', None)
                new_municipality_id = getattr(self.municipality, 'id', None)
                
                if old_municipality_id != new_municipality_id:
                    municipality_changed = True
            except Project.DoesNotExist:
                pass
        
        # Salva l'oggetto
        super().save(*args, **kwargs)
        
        # Se il comune è cambiato e non stiamo già aggiornando dei campi specifici, sincronizza i sottoprogetti
        if municipality_changed and self.municipality and kwargs.get('update_fields') is None:
            self.sync_municipalities()
    
    def __str__(self):
        return f"{self.name} - {self.region}"
    
    class Meta:
        app_label = 'projects'
        verbose_name = _("Progetto")
        verbose_name_plural = _("Progetti")