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
    # Modifica del riferimento al comune principale - ora usa il modello Municipality di Infrastructure
    municipality = models.ForeignKey('infrastructure.Municipality', on_delete=models.SET_NULL, 
                                   verbose_name=_("Comune principale"), 
                                   null=True, blank=True,
                                   related_name="core_projects")
    # Campo nascosto per debug
    _last_municipality_id = None # solo per tracciare i cambiamenti
    
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
    
    def sync_municipalities(self):
        """Sincronizza il comune di tutti i sottoprogetti con quello del progetto principale"""
        if not self.municipality:
            return False
        
        # Aggiorna tutti i sottoprogetti associati
        from .subproject import SubProject
        
        # Stampa informazioni di debug
        print(f"DEBUG sync_municipalities: Aggiornamento sottoprogetti per progetto {self.id} al comune {self.municipality.id} ({self.municipality.name})")
        print(f"DEBUG sync_municipalities: Sottoprogetti prima dell'aggiornamento: {list(SubProject.objects.filter(project=self).values('id', 'name', 'municipality_id'))}")
        
        try:
            # Aggiorna il campo municipality in tutti i sottoprogetti con un singolo update
            # per evitare cicli di salvataggio e garantire performance migliori
            updated = SubProject.objects.filter(project=self).update(municipality=self.municipality)
            
            # Verifica l'aggiornamento
            subs_after = list(SubProject.objects.filter(project=self).values('id', 'name', 'municipality_id'))
            print(f"DEBUG sync_municipalities: Sottoprogetti dopo l'aggiornamento: {subs_after}")
            print(f"DEBUG sync_municipalities: Aggiornati {updated} sottoprogetti")
            
            # Controlla che tutti i sottoprogetti abbiano l'ID municipio corretto
            incorrect = [s for s in subs_after if s['municipality_id'] != self.municipality.id]
            if incorrect:
                print(f"ERROR sync_municipalities: {len(incorrect)} sottoprogetti NON aggiornati correttamente: {incorrect}")
                
                # Tentativo di correzione forzata sui sottoprogetti non aggiornati
                for sub_id in [s['id'] for s in incorrect]:
                    try:
                        sub = SubProject.objects.get(id=sub_id)
                        sub.municipality = self.municipality
                        sub.save(skip_municipality_check=True)  # Evita ricorsione
                        print(f"INFO sync_municipalities: Forzata correzione manuale per sottoprogetto {sub_id}")
                    except Exception as sub_e:
                        print(f"ERROR sync_municipalities: Impossibile correggere manualmente {sub_id}: {sub_e}")
            
            # Aggiorna anche le stazioni di ricarica associate ai sottoprogetti
            # Questo non è necessario se le stazioni di ricarica usano sempre il comune del sottoprogetto
            # ma è una buona pratica assicurarsi che tutto sia allineato
            from .charging_station import ChargingStation
            charging_stations = ChargingStation.objects.filter(subproject__project=self)
            cs_count = charging_stations.count()
            if cs_count > 0:
                print(f"DEBUG sync_municipalities: Trovate {cs_count} stazioni di ricarica associate")
            
            return updated > 0
        except Exception as e:
            print(f"ERROR sync_municipalities: {e}")
            return False
    
    def save(self, *args, **kwargs):
        # Rimuovi l'argomento force_sync se presente (non più utilizzato)
        force_sync = kwargs.pop('force_sync', False) if 'force_sync' in kwargs else False
        
        # Tieni traccia se il municipio è cambiato
        municipality_changed = False
        if self.pk:
            old_instance = Project.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.municipality_id != getattr(self.municipality, 'id', None):
                municipality_changed = True
                print(f"DEBUG Project.save: Municipio cambiato da {old_instance.municipality_id} a {getattr(self.municipality, 'id', None)}")
                
        # Salva l'oggetto
        super().save(*args, **kwargs)
        
        # Se il comune è impostato e/o è cambiato, sincronizza i sottoprogetti
        if self.municipality and municipality_changed:
            print(f"DEBUG Project.save: Avvio sincronizzazione municipi per {self.id} - {self.name}")
            self.sync_municipalities()
            # Forza il refresh dell'istanza dal database
            self.refresh_from_db()
    
    def __str__(self):
        return f"{self.name} - {self.region}"
    
    class Meta:
        verbose_name = _("Progetto")
        verbose_name_plural = _("Progetti")