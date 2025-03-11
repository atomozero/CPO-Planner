# cpo_planner/projects/forms/photovoltaic_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.photovoltaic import PhotovoltaicSystem

class PhotovoltaicSystemForm(forms.ModelForm):
    """Form per gli impianti fotovoltaici"""
    
    class Meta:
        model = PhotovoltaicSystem
        fields = [
            'capacity', 'panel_type', 'total_area', 'number_of_panels',
            'installation_cost', 'inverter_cost', 'additional_equipment_cost',
            'expected_annual_production', 'efficiency_loss_year',
            'incentive_percentage', 'energy_sale_price',
            'installation_date', 'expected_lifespan'
        ]
        
        widgets = {
            'capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'panel_type': forms.Select(attrs={'class': 'form-control'}),
            'total_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'number_of_panels': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'inverter_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'additional_equipment_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expected_annual_production': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'efficiency_loss_year': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'incentive_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'energy_sale_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_lifespan': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Raggruppa i campi in sezioni
        self.technical_fields = [
            'capacity', 'panel_type', 'total_area', 'number_of_panels'
        ]
        
        self.cost_fields = [
            'installation_cost', 'inverter_cost', 'additional_equipment_cost'
        ]
        
        self.performance_fields = [
            'expected_annual_production', 'efficiency_loss_year'
        ]
        
        self.economic_fields = [
            'incentive_percentage', 'energy_sale_price'
        ]
        
        self.lifespan_fields = [
            'installation_date', 'expected_lifespan'
        ]