from django import forms
from django.utils.translation import gettext_lazy as _

from ..models.financial import FinancialParameters


class FinancialParametersForm(forms.ModelForm):
    """Form per i parametri finanziari"""
    
    class Meta:
        model = FinancialParameters
        fields = [
            'investment_years',
            'loan_amount',
            'loan_interest_rate',
            'loan_term',
            'pre_amortization_years',
            'market_growth_rate',
            'inflation_rate',
            'maintenance_cost_percentage',
            'energy_price_increase_rate',
            'charging_price_increase_rate',
            'failure_probability',
            'repair_cost_percentage',
        ]
        
        widgets = {
            'investment_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'loan_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'loan_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'loan_term': forms.NumberInput(attrs={'class': 'form-control'}),
            'pre_amortization_years': forms.NumberInput(attrs={'class': 'form-control'}),
            'market_growth_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'inflation_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'maintenance_cost_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'energy_price_increase_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'charging_price_increase_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'failure_probability': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'repair_cost_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }
        
        labels = {
            'investment_years': _('Durata investimento (anni)'),
            'loan_amount': _('Importo prestito (€)'),
            'loan_interest_rate': _('Tasso di interesse (%)'),
            'loan_term': _('Durata prestito (anni)'),
            'pre_amortization_years': _('Anni preammortamento'),
            'market_growth_rate': _('Crescita mercato EV (%)'),
            'inflation_rate': _('Inflazione (%)'),
            'maintenance_cost_percentage': _('Costo manutenzione (%)'),
            'energy_price_increase_rate': _('Aumento annuo prezzo energia (%)'),
            'charging_price_increase_rate': _('Aumento annuo prezzo ricarica (%)'),
            'failure_probability': _('Probabilità guasto annuale (%)'),
            'repair_cost_percentage': _('Costo riparazione (%)'),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Dividi i campi in sezioni per il template
        self.general_fields = ['investment_years']
        
        self.loan_fields = [
            'loan_amount',
            'loan_interest_rate',
            'loan_term',
            'pre_amortization_years',
        ]
        
        self.market_fields = [
            'market_growth_rate',
            'inflation_rate',
        ]
        
        self.operational_fields = [
            'maintenance_cost_percentage',
            'energy_price_increase_rate',
            'charging_price_increase_rate',
        ]
        
        self.failure_fields = [
            'failure_probability',
            'repair_cost_percentage',
        ]
