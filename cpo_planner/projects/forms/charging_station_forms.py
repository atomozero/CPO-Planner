# cpo_planner/projects/forms/charging_station_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from ..models.charging_station import ChargingStation
from cpo_core.models.charging_station import ChargingStationPhoto

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

class ChargerForm(forms.ModelForm):
    """Form per aggiungere o modificare una colonnina"""
    class Meta:
        model = None  # Temporaneamente None, lo impostiamo nel __init__
        fields = [
            'code', 'brand', 'model', 'power_kw', 'serial_number',
            'num_connectors', 'connector_types',
            'purchase_cost', 'installation_cost', 'status',
            'installation_date', 'activation_date',
            'is_fast_charging', 'is_smart_charging',
            'has_display', 'has_rfid', 'has_app_control', 'has_load_balancing'
        ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'power_kw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'num_connectors': forms.NumberInput(attrs={'class': 'form-control'}),
            'connector_types': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Es. Type 2, CCS, CHAdeMO'}),
            'purchase_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'activation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'is_fast_charging': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_smart_charging': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_display': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_rfid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_app_control': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_load_balancing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.subproject_id = kwargs.pop('subproject_id', None)
        self.charging_station_id = kwargs.pop('charging_station_id', None)
        super().__init__(*args, **kwargs)
        
        # Importa qui per evitare import circolari
        from cpo_core.models.subproject import Charger
        self._meta.model = Charger
        
        # Aggiungi note informative sui campi
        self.fields['is_fast_charging'].help_text = _("Indica se questa colonnina supporta la ricarica rapida")
        self.fields['is_smart_charging'].help_text = _("Indica se questa colonnina supporta la ricarica intelligente (con gestione dinamica della potenza)")
        self.fields['has_load_balancing'].help_text = _("Indica se questa colonnina supporta il bilanciamento del carico tra i vari connettori")


class ChargingStationPhotoForm(forms.ModelForm):
    """Form per le foto delle stazioni di ricarica"""
    
    class Meta:
        model = ChargingStationPhoto
        fields = [
            'photo', 'phase', 'title', 'description', 'date_taken'
        ]
        widgets = {
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
            'phase': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_taken': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aggiungi note informative sui campi
        self.fields['phase'].help_text = _("Seleziona la fase in cui è stata scattata la foto")
        self.fields['date_taken'].help_text = _("Data in cui è stata scattata la foto. Se lasciato vuoto, verrà usata la data odierna.")
        self.fields['photo'].help_text = _("Formati supportati: JPG, JPEG, PNG, GIF. Dimensione massima: 5MB.")