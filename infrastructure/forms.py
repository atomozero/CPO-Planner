from django import forms
from django.utils.translation import gettext_lazy as _
from .models import (
    Municipality, ChargingProject, ChargingStation, ProjectTask,
    ElectricityTariff, ManagementFee, StationUsageProfile, ChargingStationTemplate,
    GlobalSettings
)

class GlobalSettingsForm(forms.ModelForm):
    class Meta:
        model = GlobalSettings
        fields = [
            'name', 'is_active',
            'sim_data_cost_monthly', 'modem_4g_cost',
            'default_energy_cost', 'default_energy_price',
            'insurance_cost_per_station',
            'maintenance_cost_percentage',
            'public_land_fee_per_sqm',
            'vat_percentage', 'inflation_rate'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sim_data_cost_monthly': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'modem_4g_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'default_energy_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'default_energy_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'insurance_cost_per_station': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maintenance_cost_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'public_land_fee_per_sqm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'vat_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'inflation_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

class MunicipalityForm(forms.ModelForm):
    class Meta:
        model = Municipality
        fields = ['name', 'province', 'region', 'population', 'ev_adoption_rate', 'logo']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'region': forms.TextInput(attrs={'class': 'form-control'}),
            'population': forms.NumberInput(attrs={'class': 'form-control'}),
            'ev_adoption_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'})
        }

class ChargingProjectForm(forms.ModelForm):
    class Meta:
        model = ChargingProject
        fields = ['name', 'municipality', 'start_date', 'estimated_completion_date', 'budget', 'status']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'estimated_completion_date': forms.DateInput(attrs={'type': 'date'}),
            # Inizialmente nascondiamo il campo municipality standard, lo sostituiremo con Select2
            'municipality': forms.HiddenInput(),
        }
    
    # Campo personalizzato per l'autocompletamento
    municipality_autocomplete = forms.CharField(
        label=_("Comune"),
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control municipality-autocomplete'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Se stiamo modificando un progetto esistente, precompila il campo
        if self.instance and self.instance.pk and self.instance.municipality:
            self.fields['municipality_autocomplete'].initial = f"{self.instance.municipality.name} ({self.instance.municipality.province})"

class ChargingStationForm(forms.ModelForm):
    class Meta:
        model = ChargingStation
        fields = ['project', 'code', 'location', 'latitude', 'longitude', 
                 'connection_type', 'max_power', 'num_connectors',
                 'purchase_cost', 'installation_cost', 'connection_cost',
                 'ground_area', 'installation_date', 'status', 'has_pv_system', 'pv_power']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'connection_type': forms.Select(attrs={'class': 'form-select'}),
            'max_power': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'num_connectors': forms.NumberInput(attrs={'class': 'form-control'}),
            'purchase_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'connection_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'ground_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'has_pv_system': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pv_power': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

class ElectricityTariffForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aggiungi required=False ai campi che potrebbero non essere necessari in base al tipo di tariffa
        self.fields['cost_tier1'].required = False
        self.fields['cost_tier2'].required = False
        self.fields['cost_tier3'].required = False
        self.fields['cost_tier4'].required = False
        self.fields['cost_tier5'].required = False
        self.fields['pun_fee_f1'].required = False
        self.fields['pun_fee_f2'].required = False
        self.fields['pun_fee_f3'].required = False
        
        # Inizializza il campo valid_from con la data corrente se è un nuovo oggetto
        if not self.instance.pk and not self.initial.get('valid_from'):
            from datetime import date
            self.initial['valid_from'] = date.today()
    
    def clean(self):
        cleaned_data = super().clean()
        tariff_type = cleaned_data.get('tariff_type')
        
        # Verifica che i campi richiesti siano compilati in base al tipo di tariffa
        if tariff_type == 'fixed':
            # Se non è specificato il cost_tier1, usa il valore di cost_tier2
            if cleaned_data.get('cost_tier2') and not cleaned_data.get('cost_tier1'):
                cleaned_data['cost_tier1'] = cleaned_data['cost_tier2']
                
            # Imposta valori di default per gli altri tier se mancanti
            for field in ['cost_tier2', 'cost_tier3', 'cost_tier4', 'cost_tier5']:
                if not cleaned_data.get(field):
                    # Usa valori predefiniti se mancanti
                    if field == 'cost_tier2':
                        cleaned_data[field] = 0.30
                    elif field == 'cost_tier3':
                        cleaned_data[field] = 0.35
                    elif field == 'cost_tier4':
                        cleaned_data[field] = 0.40
                    elif field == 'cost_tier5':
                        cleaned_data[field] = 0.45
        
        elif tariff_type == 'pun':
            for field in ['pun_fee_f1', 'pun_fee_f2', 'pun_fee_f3']:
                if not cleaned_data.get(field):
                    # Usa valori predefiniti se mancanti
                    cleaned_data[field] = 0.02
                    
        return cleaned_data
    
    class Meta:
        model = ElectricityTariff
        fields = [
            'name', 'provider', 'active', 'tariff_type',
            'cost_tier1', 'cost_tier2', 'cost_tier3', 'cost_tier4', 'cost_tier5',
            'pun_fee_f1', 'pun_fee_f2', 'pun_fee_f3',
            'connection_fee', 'power_fee', 
            'valid_from', 'valid_to', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'provider': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tariff_type': forms.Select(attrs={'class': 'form-select', 'id': 'id_tariff_type'}),
            'cost_tier1': forms.NumberInput(attrs={'class': 'form-control fixed-price-field', 'step': '0.0001'}),
            'cost_tier2': forms.NumberInput(attrs={'class': 'form-control fixed-price-field', 'step': '0.0001'}),
            'cost_tier3': forms.NumberInput(attrs={'class': 'form-control fixed-price-field', 'step': '0.0001'}),
            'cost_tier4': forms.NumberInput(attrs={'class': 'form-control fixed-price-field', 'step': '0.0001'}),
            'cost_tier5': forms.NumberInput(attrs={'class': 'form-control fixed-price-field', 'step': '0.0001'}),
            'pun_fee_f1': forms.NumberInput(attrs={'class': 'form-control pun-price-field', 'step': '0.0001'}),
            'pun_fee_f2': forms.NumberInput(attrs={'class': 'form-control pun-price-field', 'step': '0.0001'}),
            'pun_fee_f3': forms.NumberInput(attrs={'class': 'form-control pun-price-field', 'step': '0.0001'}),
            'connection_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'power_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        
    class Media:
        js = ('js/electricity_tariff_form.js',)
        
class EnergyPriceProjectionForm(forms.Form):
    """Form per generare proiezioni di prezzo dell'energia"""
    months_ahead = forms.IntegerField(
        label=_("Mesi da proiettare"),
        min_value=1,
        max_value=36,
        initial=12,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    include_download = forms.BooleanField(
        label=_("Scarica dati PUN recenti"),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    start_date = forms.DateField(
        label=_("Data inizio (per download)"),
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        include_download = cleaned_data.get('include_download')
        start_date = cleaned_data.get('start_date')
        
        if include_download and not start_date:
            # Se non è specificata una data, imposta 3 mesi fa
            cleaned_data['start_date'] = (datetime.now() - timedelta(days=90)).date()
            
        return cleaned_data

class ManagementFeeForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendi non richiesto il campo customer_price_tier1
        self.fields['customer_price_tier1'].required = False
        
        # Inizializza la data di validità
        if not self.instance.pk and not self.initial.get('valid_from'):
            from datetime import date
            self.initial['valid_from'] = date.today()
    
    def clean(self):
        cleaned_data = super().clean()
        # Se non è stato specificato il prezzo tier1, usa il valore del tier2
        if not cleaned_data.get('customer_price_tier1') and cleaned_data.get('customer_price_tier2'):
            cleaned_data['customer_price_tier1'] = cleaned_data['customer_price_tier2']
        return cleaned_data
    
    class Meta:
        model = ManagementFee
        fields = [
            'name', 'active',
            'session_fee', 'percentage_fee', 'monthly_fee',
            'customer_price_tier1', 'customer_price_tier2', 'customer_price_tier3', 
            'customer_price_tier4', 'customer_price_tier5',
            'valid_from', 'valid_to', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'session_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'percentage_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'monthly_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'customer_price_tier1': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'customer_price_tier2': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'customer_price_tier3': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'customer_price_tier4': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'customer_price_tier5': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'valid_from': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valid_to': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class StationUsageProfileForm(forms.ModelForm):
    class Meta:
        model = StationUsageProfile
        fields = [
            'name', 'description', 'customer_profile',
            'weekday_morning_usage', 'weekday_afternoon_usage', 'weekday_evening_usage',
            'weekend_morning_usage', 'weekend_afternoon_usage', 'weekend_evening_usage',
            'avg_session_duration', 'avg_energy_per_session', 'avg_daily_sessions'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'customer_profile': forms.Select(attrs={'class': 'form-select'}),
            'weekday_morning_usage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'weekday_afternoon_usage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'weekday_evening_usage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'weekend_morning_usage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'weekend_afternoon_usage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'weekend_evening_usage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'avg_session_duration': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'avg_energy_per_session': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'avg_daily_sessions': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
        }

class ChargingStationTemplateForm(forms.ModelForm):
    class Meta:
        model = ChargingStationTemplate
        fields = [
            'name', 'brand', 'model', 'connection_type', 'power_kw', 'num_connectors', 'connector_type',
            'purchase_cost', 'installation_cost', 'maintenance_cost', 'modem_4g_cost', 'sim_annual_cost',
            'dimensions', 'weight', 'ground_area', 'protection_rating',
            'has_display', 'has_rfid', 'has_app_control', 'has_lan', 'has_wifi', 'has_4g',
            'description', 'technical_specs', 'image'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'connection_type': forms.Select(attrs={'class': 'form-select'}),
            'power_kw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'num_connectors': forms.NumberInput(attrs={'class': 'form-control'}),
            'connector_type': forms.Select(attrs={'class': 'form-select'}),
            'purchase_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'maintenance_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'modem_4g_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'sim_annual_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'dimensions': forms.TextInput(attrs={'class': 'form-control'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'ground_area': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'protection_rating': forms.TextInput(attrs={'class': 'form-control'}),
            'has_display': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_rfid': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_app_control': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_lan': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_wifi': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'has_4g': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'technical_specs': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
        }

class ProjectTaskForm(forms.ModelForm):
    class Meta:
        model = ProjectTask
        fields = ['project', 'name', 'description', 'planned_start_date', 'planned_end_date',
                 'actual_start_date', 'actual_end_date', 'priority', 'status', 'dependencies', 'responsible']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'planned_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'planned_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actual_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actual_end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'dependencies': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'responsible': forms.TextInput(attrs={'class': 'form-control'}),
        }