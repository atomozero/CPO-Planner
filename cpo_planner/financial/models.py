from django.db import models
from django.utils import timezone
from cpo_core.models import Project, SubProject, ChargingStation

class ElectricitySupplyContract(models.Model):
    """Contratto di fornitura elettrica"""
    name = models.CharField(max_length=255)
    provider = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    base_price_per_kwh = models.DecimalField(max_digits=8, decimal_places=5, help_text="Prezzo base per kWh (€)")
    peak_price_per_kwh = models.DecimalField(max_digits=8, decimal_places=5, help_text="Prezzo in orario di punta (€)")
    fixed_monthly_cost = models.DecimalField(max_digits=8, decimal_places=2, help_text="Costo fisso mensile (€)")
    power_cost_per_kw = models.DecimalField(max_digits=8, decimal_places=2, help_text="Costo per kW impegnato (€)")
    renewable_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentuale di energia rinnovabile")
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.provider}"

class FinancialProjection(models.Model):
    """Proiezione finanziaria per un progetto"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='financial_projection')
    total_investment = models.DecimalField(max_digits=12, decimal_places=2)
    equity_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=30.00, help_text="Percentuale di capitale proprio")
    loan_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=70.00, help_text="Percentuale di debito")
    expected_roi = models.DecimalField(max_digits=5, decimal_places=2, help_text="ROI atteso in percentuale")
    expected_payback_years = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tempo di payback atteso in anni")
    irr = models.DecimalField(max_digits=5, decimal_places=2, help_text="Internal Rate of Return (IRR) in percentuale")
    npv = models.DecimalField(max_digits=12, decimal_places=2, help_text="Net Present Value (NPV)")
    discount_rate = models.DecimalField(max_digits=5, decimal_places=2, default=4.00, help_text="Tasso di sconto per calcoli NPV")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Proiezione finanziaria - {self.project.name}"

class YearlyProjection(models.Model):
    """Proiezione finanziaria annuale"""
    financial_projection = models.ForeignKey(FinancialProjection, on_delete=models.CASCADE, related_name='yearly_projections')
    year = models.PositiveIntegerField()
    ev_market_penetration = models.DecimalField(max_digits=5, decimal_places=2, help_text="Penetrazione veicoli elettrici in percentuale")
    revenue = models.DecimalField(max_digits=12, decimal_places=2, help_text="Ricavi totali (€)")
    operational_costs = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costi operativi (€)")
    maintenance_costs = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costi di manutenzione (€)")
    electricity_costs = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costi elettricità (€)")
    solar_savings = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Risparmi da produzione fotovoltaica (€)")
    loan_payment = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Pagamento prestito (€)")
    depreciation = models.DecimalField(max_digits=12, decimal_places=2, help_text="Ammortamento (€)")
    ebitda = models.DecimalField(max_digits=12, decimal_places=2, help_text="EBITDA (€)")
    ebit = models.DecimalField(max_digits=12, decimal_places=2, help_text="EBIT (€)")
    taxes = models.DecimalField(max_digits=12, decimal_places=2, help_text="Tasse (€)")
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, help_text="Utile netto (€)")
    cash_flow = models.DecimalField(max_digits=12, decimal_places=2, help_text="Flusso di cassa (€)")
    cumulative_cash_flow = models.DecimalField(max_digits=12, decimal_places=2, help_text="Flusso di cassa cumulativo (€)")

    def __str__(self):
        return f"Anno {self.year} - {self.financial_projection.project.name}"

    class Meta:
        ordering = ['year']
        unique_together = [['financial_projection', 'year']]

class ChargingStationFinancials(models.Model):
    """Dati finanziari specifici per una stazione di ricarica"""
    charging_station = models.OneToOneField(ChargingStation, on_delete=models.CASCADE, related_name='financials')
    electricity_contract = models.ForeignKey(ElectricitySupplyContract, on_delete=models.SET_NULL, null=True, related_name='stations')
    
    # Tariffe
    charging_price_per_kwh = models.DecimalField(max_digits=8, decimal_places=5, help_text="Prezzo di ricarica per kWh (€)")
    charging_price_per_minute = models.DecimalField(max_digits=8, decimal_places=5, default=0, help_text="Prezzo di ricarica al minuto (€)")
    session_start_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Tariffa iniziale per sessione (€)")
    
    # Previsioni
    estimated_daily_sessions = models.DecimalField(max_digits=8, decimal_places=2, help_text="Sessioni giornaliere stimate")
    estimated_kwh_per_session = models.DecimalField(max_digits=8, decimal_places=2, help_text="kWh medi per sessione")
    estimated_annual_revenue = models.DecimalField(max_digits=12, decimal_places=2, help_text="Ricavi annuali stimati (€)")
    estimated_annual_costs = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costi annuali stimati (€)")
    estimated_annual_profit = models.DecimalField(max_digits=12, decimal_places=2, help_text="Profitto annuale stimato (€)")
    estimated_roi_years = models.DecimalField(max_digits=5, decimal_places=2, help_text="Tempo di ROI stimato in anni")
    
    # Manutenzione
    annual_maintenance_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo annuale di manutenzione (€)")
    failure_probability_year = models.DecimalField(max_digits=5, decimal_places=2, default=5.00, help_text="Probabilità di guasto annuale (%)")
    repair_cost_estimate = models.DecimalField(max_digits=10, decimal_places=2, help_text="Stima costo riparazione (€)")
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Finanza - {self.charging_station.name}"

class StationYearlyProjection(models.Model):
    """Proiezione finanziaria annuale per una stazione"""
    station_financials = models.ForeignKey(ChargingStationFinancials, on_delete=models.CASCADE, related_name='yearly_projections')
    year = models.PositiveIntegerField()
    projected_utilization = models.DecimalField(max_digits=5, decimal_places=2, help_text="Utilizzo previsto in percentuale")
    projected_sessions = models.PositiveIntegerField(help_text="Numero sessioni previste")
    projected_kwh_delivered = models.DecimalField(max_digits=12, decimal_places=2, help_text="kWh erogati previsti")
    projected_revenue = models.DecimalField(max_digits=12, decimal_places=2, help_text="Ricavi previsti (€)")
    projected_electricity_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costo elettricità previsto (€)")
    projected_maintenance_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costo manutenzione previsto (€)")
    projected_profit = models.DecimalField(max_digits=12, decimal_places=2, help_text="Profitto previsto (€)")
    failure_simulated = models.BooleanField(default=False, help_text="Se è stato simulato un guasto in questo anno")
    repair_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Costo riparazione in caso di guasto (€)")

    def __str__(self):
        return f"Anno {self.year} - {self.station_financials.charging_station.name}"

    class Meta:
        ordering = ['year']
        unique_together = [['station_financials', 'year']]

class ExitStrategy(models.Model):
    """Strategia di uscita per il progetto"""
    STRATEGY_TYPES = [
        ('sale', 'Vendita'),
        ('lease', 'Locazione'),
        ('partnership', 'Partnership'),
        ('relocation', 'Ricollocazione'),
        ('repurpose', 'Riutilizzo'),
        ('decommission', 'Dismissione'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='exit_strategies')
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPES)
    name = models.CharField(max_length=255)
    description = models.TextField()
    trigger_conditions = models.TextField(help_text="Condizioni che attivano questa strategia")
    estimated_recovery_percentage = models.DecimalField(max_digits=5, decimal_places=2, help_text="Percentuale stimata di recupero dell'investimento")
    implementation_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Costo di implementazione della strategia (€)")
    
    def __str__(self):
        return f"{self.get_strategy_type_display()} - {self.project.name}"