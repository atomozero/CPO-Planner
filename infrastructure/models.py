# models.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class Municipality(models.Model):
    name = models.CharField(_("Nome Comune"), max_length=100)
    province = models.CharField(_("Provincia"), max_length=2)
    population = models.IntegerField(_("Popolazione"), blank=True, null=True)
    ev_adoption_rate = models.FloatField(_("Tasso di adozione EV (%)"), default=2.0)
    
    class Meta:
        verbose_name = _("Comune")
        verbose_name_plural = _("Comuni")
        ordering = ["name", "province"]
    
    def __str__(self):
        return f"{self.name} ({self.province})"
    
    def potential_ev_users(self):
        """Calcola potenziali utenti di veicoli elettrici"""
        if self.population:
            return int(self.population * (self.ev_adoption_rate / 100))
        return 0


class ChargingProject(models.Model):
    name = models.CharField(_("Nome Progetto"), max_length=200)
    municipality = models.ForeignKey(
        Municipality, 
        on_delete=models.CASCADE,
        related_name="charging_projects",
        verbose_name=_("Comune")
    )
    start_date = models.DateField(_("Data di inizio"), blank=True, null=True)
    estimated_completion_date = models.DateField(_("Data di completamento stimata"), blank=True, null=True)
    actual_completion_date = models.DateField(_("Data di completamento effettiva"), blank=True, null=True)
    budget = models.DecimalField(_("Budget totale (€)"), max_digits=10, decimal_places=2, default=0)
    
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('approval', _('Approvazione')),
        ('installation', _('Installazione')),
        ('testing', _('Collaudo')),
        ('operational', _('Operativo')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='planning')
    
    class Meta:
        verbose_name = _("Progetto di ricarica")
        verbose_name_plural = _("Progetti di ricarica")
        ordering = ["municipality", "name"]
    
    def __str__(self):
        return f"{self.name} - {self.municipality}"
    
    def completion_percentage(self):
        """Calcola la percentuale di completamento del progetto"""
        # Logica da implementare basata sullo stato e sul numero di stazioni completate
        if self.status == 'operational':
            return 100
        elif self.status == 'testing':
            return 90
        elif self.status == 'installation':
            return 60
        elif self.status == 'approval':
            return 30
        else:
            return 10


class ChargingStation(models.Model):
    project = models.ForeignKey(
        ChargingProject, 
        on_delete=models.CASCADE,
        related_name="charging_stations",
        verbose_name=_("Progetto")
    )
    code = models.CharField(_("Codice identificativo"), max_length=50)
    location = models.CharField(_("Indirizzo"), max_length=255)
    latitude = models.FloatField(_("Latitudine"), blank=True, null=True)
    longitude = models.FloatField(_("Longitudine"), blank=True, null=True)
    
    # Dati tecnici
    CONNECTION_CHOICES = [
        ('ac', _('AC - Corrente Alternata')),
        ('dc', _('DC - Corrente Continua')),
        ('hybrid', _('Ibrido AC/DC')),
    ]
    connection_type = models.CharField(_("Tipo di connessione"), max_length=10, choices=CONNECTION_CHOICES)
    
    max_power = models.FloatField(_("Potenza massima (kW)"))
    num_connectors = models.IntegerField(_("Numero di connettori"), default=2)
    
    # Costi
    purchase_cost = models.DecimalField(_("Costo d'acquisto (€)"), max_digits=10, decimal_places=2)
    installation_cost = models.DecimalField(_("Costo d'installazione (€)"), max_digits=10, decimal_places=2)
    connection_cost = models.DecimalField(_("Costo di allaccio (€)"), max_digits=10, decimal_places=2)
    
    # Stati e date
    installation_date = models.DateField(_("Data di installazione"), blank=True, null=True)
    active_date = models.DateField(_("Data di attivazione"), blank=True, null=True)
    
    STATUS_CHOICES = [
        ('planned', _('Pianificata')),
        ('ordered', _('Ordinata')),
        ('installed', _('Installata')),
        ('active', _('Attiva')),
        ('maintenance', _('In manutenzione')),
        ('disabled', _('Disattivata')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Integrazione con fotovoltaico
    has_pv_system = models.BooleanField(_("Integrazione fotovoltaico"), default=False)
    pv_power = models.FloatField(_("Potenza fotovoltaico (kWp)"), blank=True, null=True)
    
    class Meta:
        verbose_name = _("Stazione di ricarica")
        verbose_name_plural = _("Stazioni di ricarica")
        ordering = ["project", "code"]
        
    def __str__(self):
        return f"{self.code} - {self.location}"
    
    def total_costs(self):
        """Calcola il costo totale della stazione"""
        return self.purchase_cost + self.installation_cost + self.connection_cost

# models.py (aggiungi questa classe)
class ProjectTask(models.Model):
    project = models.ForeignKey(
        ChargingProject, 
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name=_("Progetto")
    )
    name = models.CharField(_("Nome attività"), max_length=200)
    description = models.TextField(_("Descrizione"), blank=True)
    
    planned_start_date = models.DateField(_("Data di inizio pianificata"))
    planned_end_date = models.DateField(_("Data di fine pianificata"))
    
    actual_start_date = models.DateField(_("Data di inizio effettiva"), blank=True, null=True)
    actual_end_date = models.DateField(_("Data di fine effettiva"), blank=True, null=True)
    
    PRIORITY_CHOICES = [
        ('low', _('Bassa')),
        ('medium', _('Media')),
        ('high', _('Alta')),
    ]
    priority = models.CharField(_("Priorità"), max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    STATUS_CHOICES = [
        ('not_started', _('Non iniziata')),
        ('in_progress', _('In corso')),
        ('completed', _('Completata')),
        ('delayed', _('In ritardo')),
        ('cancelled', _('Annullata')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    dependencies = models.ManyToManyField(
        'self', 
        blank=True,
        symmetrical=False,
        related_name='dependent_tasks',
        verbose_name=_("Dipendenze")
    )
    
    responsible = models.CharField(_("Responsabile"), max_length=100, blank=True)
    
    class Meta:
        verbose_name = _("Attività di progetto")
        verbose_name_plural = _("Attività di progetto")
        ordering = ["planned_start_date", "planned_end_date"]
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"
    
    def is_delayed(self):
        """Verifica se l'attività è in ritardo"""
        from datetime import date
        if self.status == 'completed':
            return False
        return date.today() > self.planned_end_date
    
    def completion_percentage(self):
        """Calcola la percentuale di completamento dell'attività"""
        if self.status == 'completed':
            return 100
        elif self.status == 'not_started':
            return 0
        elif self.status == 'cancelled':
            return 0
        
        # Se l'attività è in corso, stima la percentuale in base al tempo trascorso
        from datetime import date
        if not self.actual_start_date:
            return 0
        
        total_days = (self.planned_end_date - self.actual_start_date).days
        if total_days <= 0:
            return 50  # Default se le date non sono valide
            
        elapsed_days = (date.today() - self.actual_start_date).days
        percentage = (elapsed_days / total_days) * 100
        
        return min(int(percentage), 99)  # Max 99% se non è completata