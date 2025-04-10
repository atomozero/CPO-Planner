# cpo_planner/projects/forms/failure_simulation_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.failure_simulation import FailureSimulation

class FailureSimulationForm(forms.ModelForm):
    """Form per la simulazione dei guasti"""
    
    class Meta:
        model = FailureSimulation
        fields = [
            'failure_rate_year1', 'failure_rate_increase',
            'minor_repair_percentage', 'major_repair_percentage', 'replacement_percentage',
            'minor_repair_cost_percentage', 'major_repair_cost_percentage',
            'average_downtime_minor', 'average_downtime_major', 'average_downtime_replacement'
        ]
        
        widgets = {
            'failure_rate_year1': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'failure_rate_increase': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'minor_repair_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'major_repair_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'replacement_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'minor_repair_cost_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'major_repair_cost_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'average_downtime_minor': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'average_downtime_major': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'average_downtime_replacement': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Raggruppa i campi in sezioni per il template
        self.rate_fields = [
            'failure_rate_year1', 'failure_rate_increase'
        ]
        
        self.type_fields = [
            'minor_repair_percentage', 'major_repair_percentage', 'replacement_percentage'
        ]
        
        self.cost_fields = [
            'minor_repair_cost_percentage', 'major_repair_cost_percentage'
        ]
        
        self.downtime_fields = [
            'average_downtime_minor', 'average_downtime_major', 'average_downtime_replacement'
        ]
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Verifica che la somma delle percentuali di tipo di guasto sia 100%
        minor = cleaned_data.get('minor_repair_percentage', 0)
        major = cleaned_data.get('major_repair_percentage', 0)
        replacement = cleaned_data.get('replacement_percentage', 0)
        
        if minor + major + replacement != 100:
            raise forms.ValidationError(
                _('La somma delle percentuali di tipi di guasto deve essere 100%')
            )
        
        return cleaned_data