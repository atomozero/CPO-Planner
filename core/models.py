from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Organization(models.Model):
    """Organizzazione che gestisce i progetti di ricarica"""
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=50, unique=True)
    address = models.TextField()
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class Project(models.Model):
    """Progetto principale che può includere più comuni"""
    STATUS_CHOICES = [
        ('planning', 'In Pianificazione'),
        ('approval', 'In Approvazione'),
        ('construction', 'In Costruzione'),
        ('operational', 'Operativo'),
        ('maintenance', 'In Manutenzione'),
        ('closed', 'Chiuso'),
    ]
    
    name = models.CharField(max_length=255)
    description = models.TextField()
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='projects')
    project_manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='managed_projects')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField()
    end_date = models.DateField()
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    loan_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    loan_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    loan_term_years = models.PositiveIntegerField(default=10)
    pre_amortization_years = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name

class Municipality(models.Model):
    """Comune in cui vengono installate le stazioni di ricarica"""
    name = models.CharField(max_length=255)
    province = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    population = models.PositiveIntegerField()
    area_sqkm = models.DecimalField(max_digits=10, decimal_places=2)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.province})"
    
    class Meta:
        verbose_name_plural = "Municipalities"

class SubProject(models.Model):
    """Sotto-progetto per un comune specifico"""
    STATUS_CHOICES = [
        ('planning', 'In Pianificazione'),
        ('permit', 'Richiesta Permessi'),
        ('approval', 'In Approvazione'),
        ('construction', 'In Costruzione'),
        ('operational', 'Operativo'),
        ('maintenance', 'In Manutenzione'),
        ('closed', 'Chiuso'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='subprojects')
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name='subprojects')
    name = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning')
    start_date = models.DateField()
    planned_completion_date = models.DateField()
    actual_completion_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='responsible_for_subprojects')
    
    def __str__(self):
        return f"{self.name} - {self.municipality.name}"

class ChargingStation(models.Model):
    """Stazione di ricarica"""
    STATION_TYPES = [
        ('ac_slow', 'AC Lenta (fino a 7.4 kW)'),
        ('ac_fast', 'AC Veloce (11-22 kW)'),
        ('dc_fast', 'DC Veloce (50 kW)'),
        ('hpc', 'High Power Charger (>100 kW)'),
    ]
    STATUS_CHOICES = [
        ('planned', 'Pianificata'),
        ('permitting', 'In Fase di Autorizzazione'),
        ('installing', 'In Installazione'),
        ('testing', 'In Test'),
        ('operational', 'Operativa'),
        ('maintenance', 'In Manutenzione'),
        ('offline', 'Fuori Servizio'),
        ('decommissioned', 'Dismessa'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subproject = models.ForeignKey(SubProject, on_delete=models.CASCADE, related_name='charging_stations')
    name = models.CharField(max_length=255)
    station_type = models.CharField(max_length=20, choices=STATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    address = models.TextField()
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    installation_date = models.DateField(null=True, blank=True)
    activation_date = models.DateField(null=True, blank=True)
    
    # Costi
    connection_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo per l'allaccio")
    installation_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo di installazione")
    hardware_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo dell'hardware")
    design_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo di progettazione")
    permit_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo dei permessi")
    other_costs = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Altri costi")
    
    # Specifiche tecniche
    power_kw = models.DecimalField(max_digits=8, decimal_places=2, help_text="Potenza in kW")
    connector_types = models.CharField(max_length=255, help_text="Tipi di connettori separati da virgola")
    num_connectors = models.PositiveIntegerField(default=2)
    grid_connection_capacity = models.DecimalField(max_digits=8, decimal_places=2, help_text="Capacità di connessione alla rete in kW")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_station_type_display()})"
    
    @property
    def total_cost(self):
        """Calcola il costo totale della stazione"""
        return (
            self.connection_cost + 
            self.installation_cost + 
            self.hardware_cost + 
            self.design_cost + 
            self.permit_cost + 
            self.other_costs
        )

class SolarInstallation(models.Model):
    """Impianto fotovoltaico associato a una stazione di ricarica"""
    charging_station = models.OneToOneField(ChargingStation, on_delete=models.CASCADE, related_name='solar_installation')
    capacity_kw = models.DecimalField(max_digits=8, decimal_places=2, help_text="Capacità in kW")
    panel_type = models.CharField(max_length=100)
    num_panels = models.PositiveIntegerField()
    installation_cost = models.DecimalField(max_digits=10, decimal_places=2)
    annual_production_kwh = models.DecimalField(max_digits=10, decimal_places=2, help_text="Produzione annuale stimata in kWh")
    installation_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Impianto FV {self.capacity_kw}kW - {self.charging_station.name}"