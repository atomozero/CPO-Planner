# forms.py
from django import forms
from .models import Municipality, ChargingProject, ChargingStation, ProjectTask  
from django.utils.translation import gettext_lazy as _

class MunicipalityForm(forms.ModelForm):
    class Meta:
        model = Municipality
        fields = ['name', 'province', 'population', 'ev_adoption_rate']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'population': forms.NumberInput(attrs={'class': 'form-control'}),
            'ev_adoption_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
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
                 'installation_date', 'status', 'has_pv_system', 'pv_power']
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
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'has_pv_system': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'pv_power': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
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