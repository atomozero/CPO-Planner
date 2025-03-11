from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import random

class FinancialProjection(models.Model):
    """Modello per le proiezioni finanziarie di un progetto"""
    project = models.OneToOneField('Project', on_delete=models.CASCADE, related_name='financial_projection_core')
    total_investment = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Investimento totale (€)")
    )
    expected_roi = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name=_("ROI atteso (%)")
    )
    roi = models.DecimalField(
        max_digits=6, decimal_places=2, default=0,
        verbose_name=_("ROI calcolato (%)")
    )
    payback_period = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        verbose_name=_("Periodo di recupero (anni)")
    )
    loan_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Importo prestito (€)")
    )
    loan_interest_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=3.5,
        verbose_name=_("Tasso di interesse (%)")
    )
    loan_term = models.IntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        verbose_name=_("Durata prestito (anni)")
    )
    grace_period = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name=_("Preammortamento (anni)")
    )
    electricity_price_kwh = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.25,
        verbose_name=_("Prezzo elettricità (€/kWh)")
    )
    charging_price_kwh = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.45,
        verbose_name=_("Prezzo ricarica (€/kWh)")
    )
    include_solar = models.BooleanField(
        default=False,
        verbose_name=_("Includere impianto fotovoltaico")
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
        from .charging_station import ChargingStation
        
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
            annual_maintenance = sum(station.station_cost * 0.05 for station in charging_stations) * maintenance_factor
            
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
                    repair_cost = random.uniform(0.05, 0.20) * station.station_cost
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
    year = models.IntegerField(verbose_name=_("Anno"))
    revenue = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Ricavi (€)")
    )
    operating_expenses = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Spese operative (€)")
    )
    loan_payment = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Rata prestito (€)")
    )
    maintenance_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Costi manutenzione (€)")
    )
    electricity_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Costi elettricità (€)")
    )
    net_profit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Utile netto (€)")
    )
    
    class Meta:
        unique_together = ('financial_projection', 'year')
        ordering = ['year']
    
    def __str__(self):
        return f"{self.financial_projection.project.name} - Anno {self.year}"