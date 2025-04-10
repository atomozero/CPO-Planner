# environmental/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from projects.models.project import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.charging_station import ChargingStation

from .models import (
    EnvironmentalAnalysis, YearlyEnvironmentalData,
    EmissionFactor, VehicleType
)

class EmissionFactorForm(forms.ModelForm):
    """Form per la creazione e modifica dei fattori di emissione"""
    class Meta:
        model = EmissionFactor
        fields = [
            'name', 'source_type', 'emission_factor', 'year', 
            'country', 'source', 'notes', 'is_default'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'source_type': forms.Select(attrs={'class': 'form-control'}),
            'emission_factor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'year': forms.NumberInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'source': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Imposta l'anno corrente come predefinito per i nuovi record
        if not self.instance.pk:
            self.fields['year'].initial = timezone.now().year
            
    def save(self, commit=True):
        emission_factor = super().save(commit=False)
        
        if self.user and not emission_factor.pk:
            emission_factor.created_by = self.user
            
        if commit:
            emission_factor.save()
            
        return emission_factor

class VehicleTypeForm(forms.ModelForm):
    """Form per la creazione e modifica dei tipi di veicolo"""
    class Meta:
        model = VehicleType
        fields = [
            'name', 'description', 'avg_consumption', 'avg_ice_consumption',
            'fuel_type', 'battery_capacity', 'avg_range', 'market_share'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avg_consumption': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'avg_ice_consumption': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'fuel_type': forms.Select(attrs={'class': 'form-control'}),
            'battery_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'avg_range': forms.NumberInput(attrs={'class': 'form-control', 'step': '1'}),
            'market_share': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0', 'max': '100'})
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
            
    def save(self, commit=True):
        vehicle_type = super().save(commit=False)
        
        if self.user and not vehicle_type.pk:
            vehicle_type.created_by = self.user
            
        if commit:
            vehicle_type.save()
            
        return vehicle_type

class EnvironmentalAnalysisForm(forms.ModelForm):
    """Form per la creazione e modifica dell'analisi ambientale"""
    
    # Campo per selezionare il tipo di entità
    entity_type = forms.ChoiceField(
        label=_('Tipo di Entità'),
        choices=[
            ('', _('Nessuna entità - Analisi Globale')),
            ('project', _('Progetto')),
            ('subproject', _('Sotto-progetto')),
            ('chargingstation', _('Stazione di ricarica')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Campi dinamici per selezionare l'entità specifica
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        label=_('Progetto'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subproject = forms.ModelChoiceField(
        queryset=SubProject.objects.all(),
        label=_('Sotto-progetto'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    chargingstation = forms.ModelChoiceField(
        queryset=ChargingStation.objects.all(),
        label=_('Stazione di ricarica'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = EnvironmentalAnalysis
        fields = [
            'name', 'description', 'start_date', 'end_date',
            'years_projection', 'electricity_emission_factor',
            'fuel_emission_factor', 'renewable_percentage',
            'avg_sessions_per_day', 'avg_kwh_per_session', 'utilization_rate'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'years_projection': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'max': '30'}),
            'electricity_emission_factor': forms.Select(attrs={'class': 'form-control'}),
            'fuel_emission_factor': forms.Select(attrs={'class': 'form-control'}),
            'renewable_percentage': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'}),
            'avg_sessions_per_day': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'avg_kwh_per_session': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'utilization_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '1', 'min': '0', 'max': '100'})
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Imposta le opzioni predefinite per i fattori di emissione
        self.fields['electricity_emission_factor'].queryset = EmissionFactor.objects.filter(
            source_type=EmissionFactor.EnergySourceType.ELECTRICITY_MIX
        )
        self.fields['fuel_emission_factor'].queryset = EmissionFactor.objects.filter(
            source_type__in=[
                EmissionFactor.EnergySourceType.GASOLINE,
                EmissionFactor.EnergySourceType.DIESEL
            ]
        )
        
        # Se è un'istanza esistente, precompila i campi
        if self.instance.pk and self.instance.content_type:
            content_type = self.instance.content_type
            if content_type.model == 'project':
                self.fields['entity_type'].initial = 'project'
                self.fields['project'].initial = self.instance.object_id
            elif content_type.model == 'subproject':
                self.fields['entity_type'].initial = 'subproject'
                self.fields['subproject'].initial = self.instance.object_id
            elif content_type.model == 'chargingstation':
                self.fields['entity_type'].initial = 'chargingstation'
                self.fields['chargingstation'].initial = self.instance.object_id
        
    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        
        # Verifica che sia selezionata un'entità valida se è specificato il tipo
        if entity_type:
            entity_obj = None
            if entity_type == 'project':
                entity_obj = cleaned_data.get('project')
            elif entity_type == 'subproject':
                entity_obj = cleaned_data.get('subproject')
            elif entity_type == 'chargingstation':
                entity_obj = cleaned_data.get('chargingstation')
            
            if not entity_obj:
                raise forms.ValidationError(_('Seleziona un\'entità valida per il tipo selezionato.'))
                
        return cleaned_data
    
    def save(self, commit=True):
        analysis = super().save(commit=False)
        
        # Imposta il content_type e object_id in base all'entità selezionata
        entity_type = self.cleaned_data.get('entity_type')
        if entity_type:
            if entity_type == 'project':
                entity_obj = self.cleaned_data.get('project')
                content_type = ContentType.objects.get_for_model(Project)
            elif entity_type == 'subproject':
                entity_obj = self.cleaned_data.get('subproject')
                content_type = ContentType.objects.get_for_model(SubProject)
            elif entity_type == 'chargingstation':
                entity_obj = self.cleaned_data.get('chargingstation')
                content_type = ContentType.objects.get_for_model(ChargingStation)
            
            analysis.content_type = content_type
            analysis.object_id = entity_obj.id
        else:
            analysis.content_type = None
            analysis.object_id = None
        
        # Imposta l'utente creatore
        if self.user and not analysis.pk:
            analysis.created_by = self.user
            
        if commit:
            analysis.save()
            
        return analysis

class EnvironmentalAnalysisFilterForm(forms.Form):
    """Form per filtrare le analisi ambientali"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Cerca per nome o descrizione...')
        })
    )
    
    entity_type = forms.ChoiceField(
        choices=[
            ('', _('Tutte le entità')),
            ('project', _('Progetti')),
            ('subproject', _('Sotto-progetti')),
            ('chargingstation', _('Stazioni di ricarica')),
            ('none', _('Nessuna entità')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': _('Da data')
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': _('A data')
        })
    )
