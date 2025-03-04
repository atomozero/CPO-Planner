# cpo_planner/projects/forms/charging_station_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.charging_station import ChargingStation

class ChargingStationForm(forms.ModelForm):
    """Form per le stazioni di ricarica"""
    
    class Meta:
        model = ChargingStation
        fields = [
            'name', 'identifier', 'address', 'latitude', 'longitude',
            'power_type', 'charging_points', 'total_power',
            'station_cost', 'installation_cost', 'connection_cost',
            'design_cost', 'permit_cost', 'energy_cost_kwh',
            'charging_price_kwh', 'estimated_sessions_day',
            'avg_kwh_session', 'installation_date', 'status'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'power_type': forms.Select(attrs={'class': 'form-control'}),
            'charging_points': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'total_power': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'station_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'connection_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'design_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'permit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'energy_cost_kwh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'charging_price_kwh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'estimated_sessions_day': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'avg_kwh_session': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Raggruppa i campi in sezioni per il template
        self.identification_fields = [
            'name', 'identifier', 'address', 'latitude', 'longitude'
        ]
        
        self.technical_fields = [
            'power_type', 'charging_points', 'total_power'
        ]
        
        self.cost_fields = [
            'station_cost', 'installation_cost', 'connection_cost',
            'design_cost', 'permit_cost'
        ]
        
        self.operational_fields = [
            'energy_cost_kwh', 'charging_price_kwh',
            'estimated_sessions_day', 'avg_kwh_session'
        ]
        
        self.status_fields = [
            'installation_date', 'status'
        ]