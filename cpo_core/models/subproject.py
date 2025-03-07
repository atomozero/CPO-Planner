from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from infrastructure.models import StationUsageProfile

class StationImage(models.Model):
    """Immagini delle stazioni di ricarica"""
    subproject = models.ForeignKey('SubProject', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='charging_stations/', blank=True, null=True)
    title = models.CharField(_("Titolo"), max_length=100, blank=True, null=True)
    description = models.TextField(_("Descrizione"), blank=True, null=True)
    is_before_installation = models.BooleanField(_("Prima dell'installazione"), default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Immagine per {self.subproject.name} - {self.title or 'Senza titolo'}"
    
    class Meta:
        verbose_name = _("Immagine Stazione")
        verbose_name_plural = _("Immagini Stazioni")
        
class Charger(models.Model):
    """Singola colonnina all'interno di una stazione di ricarica"""
    subproject = models.ForeignKey('SubProject', on_delete=models.CASCADE, related_name='chargers', null=True, blank=True)
    charging_station = models.ForeignKey('ChargingStation', on_delete=models.CASCADE, related_name='chargers', null=True, blank=True)
    
    # Dati colonnina
    code = models.CharField(_("Codice colonnina"), max_length=100)
    brand = models.CharField(_("Marca"), max_length=100, blank=True, null=True)
    model = models.CharField(_("Modello"), max_length=100, blank=True, null=True)
    power_kw = models.DecimalField(_("Potenza (kW)"), max_digits=8, decimal_places=2, null=True, blank=True)
    serial_number = models.CharField(_("Numero seriale"), max_length=100, blank=True, null=True)
    
    # Connettori
    num_connectors = models.PositiveIntegerField(_("Numero Connettori"), default=1)
    connector_types = models.CharField(_("Tipi di Connettori"), max_length=255, blank=True, null=True,
                                 help_text=_("Separati da virgola, esempio: Type 2, CCS, CHAdeMO"))
    
    # Costi
    purchase_cost = models.DecimalField(_("Costo d'acquisto (€)"), max_digits=10, decimal_places=2, null=True, blank=True)
    installation_cost = models.DecimalField(_("Costo d'installazione (€)"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stato
    STATUS_CHOICES = [
        ('operational', _('Operativa')),
        ('maintenance', _('In Manutenzione')),
        ('offline', _('Non Operativa')),
        ('planned', _('Pianificata')),
        ('installing', _('In Installazione')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Date
    installation_date = models.DateField(_("Data installazione"), null=True, blank=True)
    activation_date = models.DateField(_("Data attivazione"), null=True, blank=True)
    
    # Specifiche tecniche
    is_fast_charging = models.BooleanField(_("Ricarica rapida"), default=False)
    is_smart_charging = models.BooleanField(_("Smart charging"), default=False)
    has_display = models.BooleanField(_("Display"), default=True)
    has_rfid = models.BooleanField(_("Lettore RFID"), default=True)
    has_app_control = models.BooleanField(_("Controllo da app"), default=True)
    has_load_balancing = models.BooleanField(_("Load balancing"), default=False)
    
    def __str__(self):
        return f"{self.code} - {self.brand} {self.model}, {self.power_kw}kW"
    
    class Meta:
        verbose_name = _("Colonnina")
        verbose_name_plural = _("Colonnine")
        ordering = ["code"]

class SubProject(models.Model):
    """Sotto-progetto per un comune specifico"""
    # Relazioni
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='subprojects', verbose_name=_('Progetto Principale'))
    municipality = models.ForeignKey('Municipality', on_delete=models.CASCADE, related_name='subprojects', verbose_name=_('Comune'))
    
    # Informazioni di base
    name = models.CharField(_("Nome Sottoprogetto"), max_length=255)
    description = models.TextField(_("Descrizione"), blank=True, null=True)
    
    # Localizzazione
    address = models.CharField(_("Indirizzo"), max_length=255, blank=True, null=True)
    cadastral_data = models.CharField(_("Dati Catastali"), max_length=255, blank=True, null=True, 
                                    help_text=_("Foglio, Particella, Subalterno"))
    latitude_proposed = models.DecimalField(_("Latitudine Proposta"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_proposed = models.DecimalField(_("Longitudine Proposta"), max_digits=9, decimal_places=6, null=True, blank=True)
    latitude_approved = models.DecimalField(_("Latitudine Approvata"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_approved = models.DecimalField(_("Longitudine Approvata"), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Dettagli colonnine
    charger_brand = models.CharField(_("Marca Colonnina"), max_length=100, blank=True, null=True)
    charger_model = models.CharField(_("Modello Colonnina"), max_length=100, blank=True, null=True)
    power_kw = models.DecimalField(_("Potenza (kW)"), max_digits=8, decimal_places=2, null=True, blank=True)
    power_requested = models.DecimalField(_("Potenza Richiesta a E-Distribuzione (kW)"), max_digits=8, decimal_places=2, null=True, blank=True)
    connector_types = models.CharField(_("Tipi di Connettori"), max_length=255, blank=True, null=True,
                                     help_text=_("Separati da virgola, esempio: Type 2, CCS, CHAdeMO"))
    num_connectors = models.PositiveIntegerField(_("Numero Connettori"), default=1)
    num_chargers = models.PositiveIntegerField(_("Numero Colonnine"), default=1)
    ground_area_sqm = models.DecimalField(_("Area Occupata (m²)"), max_digits=6, decimal_places=2, null=True, blank=True)
    usage_profile = models.ForeignKey(StationUsageProfile, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='charging_stations', verbose_name=_('Profilo di Consumo'))
    
    # Timeline
    start_date = models.DateField(_("Data Inizio"), default="2023-01-01")
    planned_completion_date = models.DateField(_("Data Prevista Completamento"), default="2023-12-31")
    actual_completion_date = models.DateField(_("Data Effettiva Completamento"), null=True, blank=True)
    use_project_completion_date = models.BooleanField(_("Usa Data Completamento Progetto"), default=False)
    
    # Informazioni finanziarie
    budget = models.DecimalField(_("Budget Totale"), max_digits=12, decimal_places=2, default=0)
    expected_revenue = models.DecimalField(_("Ricavi Attesi"), max_digits=12, decimal_places=2, default=0)
    roi = models.DecimalField(_("ROI"), max_digits=10, decimal_places=2, default=0, validators=[
        MinValueValidator(Decimal('-99.99')), 
        MaxValueValidator(Decimal('9999.99'))
    ])
    
    # Dettaglio costi
    equipment_cost = models.DecimalField(_("Costo Colonnina"), max_digits=10, decimal_places=2, null=True, blank=True)
    installation_cost = models.DecimalField(_("Costo Installazione"), max_digits=10, decimal_places=2, null=True, blank=True)
    connection_cost = models.DecimalField(_("Costo Allaccio Rete"), max_digits=10, decimal_places=2, null=True, blank=True)
    permit_cost = models.DecimalField(_("Costo Permessi"), max_digits=10, decimal_places=2, null=True, blank=True)
    civil_works_cost = models.DecimalField(_("Costo Opere Civili"), max_digits=10, decimal_places=2, null=True, blank=True)
    other_costs = models.DecimalField(_("Altri Costi"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Personale
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='responsible_for_subprojects', blank=True)
    
    # Stato
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('permit', _('Richiesta Permessi')),
        ('approval', _('In Approvazione')),
        ('construction', _('In Costruzione')),
        ('in_progress', _('In Corso')),
        ('operational', _('Operativo')),
        ('maintenance', _('In Manutenzione')),
        ('completed', _('Completato')),
        ('suspended', _('Sospeso')),
        ('closed', _('Chiuso'))
    ]
    status = models.CharField(_("Stato Sotto-Progetto"), max_length=20, choices=STATUS_CHOICES, default='planning')
    status_changed_date = models.DateTimeField(_("Data Cambio Stato"), auto_now=False, null=True, blank=True)
    status_changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='status_changes', verbose_name=_('Cambio Stato Da'))
    
    def save(self, *args, **kwargs):
        # Gestione delle date in base al progetto
        if not self.pk:  # Solo per nuovi oggetti
            if self.start_date < self.project.start_date:
                self.start_date = self.project.start_date
                
            if self.use_project_completion_date:
                self.planned_completion_date = self.project.expected_completion_date
            elif self.planned_completion_date > self.project.expected_completion_date:
                self.planned_completion_date = self.project.expected_completion_date
        
        # Calcola il costo di connessione se non specificato ma è stata specificata la potenza richiesta
        if self.power_requested and (self.connection_cost is None or self.connection_cost == 0):
            self.connection_cost = self.power_requested * 80  # 80€ per kW
        
        # Calcola il budget totale sommando i costi
        total_cost = sum(filter(None, [
            self.equipment_cost or 0,
            self.installation_cost or 0, 
            self.connection_cost or 0,
            self.permit_cost or 0,
            self.civil_works_cost or 0,
            self.other_costs or 0
        ]))
        if total_cost > 0:
            self.budget = total_cost
            
        # Calcola i ricavi attesi e il ROI se c'è un profilo di utilizzo
        if self.usage_profile and self.power_kw:
            # Ricavi mensili stimati in base al profilo di utilizzo
            monthly_usage = self.usage_profile.calculate_monthly_usage(float(self.power_kw))
            # Assumiamo un prezzo medio di vendita di 0.45€/kWh
            monthly_revenue = monthly_usage * 0.45
            annual_revenue = monthly_revenue * 12
            self.expected_revenue = annual_revenue
            
            # Calcolo ROI
            if self.budget and self.budget > 0:
                # ROI annuo = (ricavi annuali / investimento totale) * 100
                self.roi = (annual_revenue / float(self.budget)) * 100
        
        super().save(*args, **kwargs)
        # Aggiorna le metriche del progetto principale dopo il salvataggio
        self.project.calculate_total_metrics()
    
    def __str__(self):
        return f"{self.name} - {self.municipality}"
    
    class Meta:
        verbose_name = _("Sotto-Progetto")
        verbose_name_plural = _("Sotto-Progetti")