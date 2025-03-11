# cpo_core/models.py
# Manteniamo questo file per retrocompatibilità
# Tutte le definizioni dei modelli sono state spostate nei file nella cartella models/

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import random
import uuid

# Importa i modelli consolidati
from .models.organization import Organization
from .models.project import Project
from .models.municipality import Municipality
from .models.subproject import SubProject
from .models.charging_station import ChargingStation, SolarInstallation

class FinancialProjection(models.Model):
    """Modello per le proiezioni finanziarie di un progetto"""
    project = models.OneToOneField('Project', on_delete=models.CASCADE, related_name='cpo_financial_projection')
    total_investment = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Investimento totale (€)"
    )
    expected_roi = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name="ROI atteso (%)"
    )
    roi = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name="ROI calcolato (%)"
    )
    payback_period = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name="Periodo di recupero (anni)"
    )
    loan_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Importo prestito (€)"
    )
    loan_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=3.5,
        verbose_name="Tasso di interesse (%)"
    )
    loan_term = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name="Durata prestito (anni)"
    )
    grace_period = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="Preammortamento (anni)"
    )
    electricity_price_kwh = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.25,
        verbose_name="Prezzo elettricità (€/kWh)"
    )
    charging_price_kwh = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.45,
        verbose_name="Prezzo ricarica (€/kWh)"
    )
    include_solar = models.BooleanField(
        default=False,
        verbose_name="Includere impianto fotovoltaico"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Proiezione finanziaria - {self.project.name}"
    
    def save(self, *args, **kwargs):
        """Override del metodo save per calcolare automaticamente alcuni valori"""
        # Calcola il ROI e altri valori se questo è un nuovo oggetto
        if not self.pk:
            self.calculate_financial_projections()
        
        super().save(*args, **kwargs)
    
    def calculate_financial_projections(self):
        """Calcola le proiezioni finanziarie del progetto"""
        from .models import ChargingStation, YearlyProjection
        
        # Recupera tutte le stazioni di ricarica del progetto
        charging_stations = ChargingStation.objects.filter(
            subproject__project=self.project
        )
        
        # Calcola l'investimento totale
        total_investment = sum(station.calculate_total_cost() for station in charging_stations)
        self.total_investment = total_investment
        
        # Se ci sono stazioni, procedi con gli altri calcoli
        if charging_stations.exists():
            # Calcola entrate e uscite annuali
            yearly_data = self.calculate_yearly_financials(charging_stations)
            
            # Calcola ROI e periodo di recupero
            total_revenue = sum(year['revenue'] for year in yearly_data)
            total_expenses = sum(year['operating_expenses'] for year in yearly_data)
            total_profit = total_revenue - total_expenses
            
            if total_investment > 0:
                self.roi = (total_profit / total_investment) * 100
            
            # Calcola il periodo di recupero (payback period)
            cumulative_cash_flow = 0
            for i, year in enumerate(yearly_data, 1):
                yearly_profit = year['revenue'] - year['operating_expenses']
                cumulative_cash_flow += yearly_profit
                
                if cumulative_cash_flow >= total_investment:
                    # Interpolazione lineare per periodo esatto
                    prev_cash_flow = cumulative_cash_flow - yearly_profit
                    fraction = (total_investment - prev_cash_flow) / yearly_profit
                    self.payback_period = i - 1 + fraction
                    break
            
            # Crea o aggiorna le proiezioni annuali
            for i, year_data in enumerate(yearly_data):
                YearlyProjection.objects.update_or_create(
                    financial_projection=self,
                    year=i + 1,
                    defaults={
                        'revenue': year_data['revenue'],
                        'operating_expenses': year_data['operating_expenses'],
                        'loan_payment': year_data['loan_payment'],
                        'maintenance_cost': year_data['maintenance_cost'],
                        'electricity_cost': year_data['electricity_cost'],
                        'net_profit': year_data['revenue'] - year_data['operating_expenses'],
                    }
                )
    
    def calculate_yearly_financials(self, charging_stations):
        """Calcola i dati finanziari annuali per i 10 anni di proiezione"""
        yearly_data = []
        
        # Calcola i parametri di base
        total_connectors = sum(station.num_connectors for station in charging_stations)
        avg_power = sum(station.power_kw for station in charging_stations) / len(charging_stations) if charging_stations else 0
        
        # Parametri del prestito
        loan_amount = self.loan_amount or self.total_investment
        monthly_rate = (self.loan_interest_rate / 100) / 12
        loan_term_months = self.loan_term * 12
        grace_period_months = self.grace_period * 12
        
        # Calcola la rata mensile del prestito (escludendo periodo di preammortamento)
        if monthly_rate > 0:
            monthly_payment = loan_amount * monthly_rate * (1 + monthly_rate) ** loan_term_months / ((1 + monthly_rate) ** loan_term_months - 1)
        else:
            monthly_payment = loan_amount / loan_term_months
        
        # Genera dati per 10 anni
        for year in range(1, 11):
            # Fattore di crescita dell'utilizzo basato sull'anno
            # Inizia basso e cresce fino al 100% entro l'anno 5
            usage_factor = min(1.0, 0.4 + (year - 1) * 0.15)
            
            # Media delle sessioni giornaliere per connettore
            # Dipende dall'anno (crescita di mercato) e dalla potenza media delle stazioni
            avg_daily_sessions = min(7, 2 + year * 0.5) * usage_factor
            
            # kWh medi erogati per sessione (correlati alla potenza media)
            avg_kwh_per_session = min(30, 10 + avg_power * 0.5) * usage_factor
            
            # Calcola ricavi annuali
            daily_revenue = (total_connectors * avg_daily_sessions * avg_kwh_per_session * self.charging_price_kwh)
            annual_revenue = daily_revenue * 365
            
            # Calcola i costi di manutenzione (crescono col tempo)
            maintenance_factor = 1 + (year - 1) * 0.05  # +5% all'anno
            annual_maintenance = sum(station.financials.yearly_maintenance_cost for station in charging_stations) * maintenance_factor
            
            # Calcola i costi dell'elettricità (85% dei ricavi lordi come stima)
            annual_electricity_cost = total_connectors * avg_daily_sessions * avg_kwh_per_session * self.electricity_price_kwh * 365
            
            # Calcola i pagamenti del prestito per l'anno
            if year <= self.grace_period:
                # Solo interessi durante il preammortamento
                annual_loan_payment = loan_amount * (self.loan_interest_rate / 100)
            else:
                # Rata completa dopo il preammortamento
                annual_loan_payment = monthly_payment * 12
            
            # Simula guasti casuali (aggiunge costi di manutenzione straordinaria)
            # Probabilità di guasto aumenta con l'età delle stazioni
            fault_probability = 0.02 + (year - 1) * 0.01  # Parte da 2% e aumenta dell'1% all'anno
            
            extraordinary_maintenance = 0
            for station in charging_stations:
                if random.random() < fault_probability:
                    # Costo di riparazione stimato tra il 5% e il 20% del costo dell'apparecchiatura
                    repair_cost = random.uniform(0.05, 0.20) * station.financials.equipment_cost
                    extraordinary_maintenance += repair_cost
            
            # Calcola spese operative totali
            operating_expenses = annual_maintenance + annual_electricity_cost + extraordinary_maintenance
            
            # Aggiungi dati dell'anno alla lista
            yearly_data.append({
                'year': year,
                'revenue': Decimal(str(annual_revenue)),
                'operating_expenses': Decimal(str(operating_expenses)),
                'loan_payment': Decimal(str(annual_loan_payment)),
                'maintenance_cost': Decimal(str(annual_maintenance + extraordinary_maintenance)),
                'electricity_cost': Decimal(str(annual_electricity_cost)),
                'usage_factor': usage_factor,
                'daily_sessions': total_connectors * avg_daily_sessions,
            })
        
        return yearly_data

class YearlyProjection(models.Model):
    """Proiezioni finanziarie annuali per un progetto"""
    financial_projection = models.ForeignKey(
        FinancialProjection, on_delete=models.CASCADE, related_name='yearly_projections'
    )
    year = models.IntegerField(verbose_name="Anno")
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Ricavi (€)"
    )
    operating_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Spese operative (€)"
    )
    loan_payment = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Rata prestito (€)"
    )
    maintenance_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Costi manutenzione (€)"
    )
    electricity_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Costi elettricità (€)"
    )
    net_profit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Utile netto (€)"
    )
    
    class Meta:
        unique_together = ('financial_projection', 'year')
        ordering = ['year']
    
    def __str__(self):
        return f"{self.financial_projection.project.name} - Anno {self.year}"

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