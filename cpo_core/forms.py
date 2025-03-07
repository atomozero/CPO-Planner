from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import (
    Organization, Project, Municipality, SubProject, ChargingStation, 
    FinancialProjection, YearlyProjection, SolarInstallation
)
# Importa modelli consolidati
from .models.organization import Organization
from .models.project import Project
from .models.municipality import Municipality 
from .models.subproject import SubProject
from .models.charging_station import ChargingStation, SolarInstallation
from .models.financial import FinancialProjection, YearlyProjection

class FinancialProjectionForm(forms.ModelForm):
    """Form per la creazione e l'aggiornamento delle proiezioni finanziarie."""
    
    class Meta:
        model = FinancialProjection
        fields = [
            'expected_roi', 'loan_amount', 'loan_interest_rate', 'loan_term',
            'grace_period', 'electricity_price_kwh', 'charging_price_kwh', 'include_solar'
        ]
        widgets = {
            'expected_roi': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_term': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'grace_period': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 5}),
            'electricity_price_kwh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'charging_price_kwh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.0001'}),
            'include_solar': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        loan_term = cleaned_data.get('loan_term')
        grace_period = cleaned_data.get('grace_period')
        
        if loan_term and grace_period and grace_period >= loan_term:
            raise forms.ValidationError(
                "Il periodo di preammortamento non può essere maggiore o uguale alla durata del prestito."
            )
        
        return cleaned_data

class OrganizationForm(forms.ModelForm):
    """Form per la gestione delle organizzazioni."""
    
    class Meta:
        model = Organization
        fields = ['name', 'tax_id', 'address', 'contact_email', 'contact_phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProjectForm(forms.ModelForm):
    """Form per la gestione dei progetti."""
    
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'organization', 'project_manager', 'logo',
            'status', 'start_date', 'expected_completion_date', 'total_budget', 
            'loan_amount', 'loan_interest_rate', 'loan_term_years', 'pre_amortization_years'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'organization': forms.Select(attrs={'class': 'form-control'}),
            'project_manager': forms.Select(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'total_budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_interest_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'loan_term_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'pre_amortization_years': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 5}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        expected_completion_date = cleaned_data.get('expected_completion_date')
        
        if start_date and expected_completion_date and expected_completion_date < start_date:
            raise forms.ValidationError(
                "La data di fine progetto non può essere precedente alla data di inizio."
            )
        
        return cleaned_data

class MunicipalityForm(forms.ModelForm):
    """Form per la gestione dei comuni."""
    
    class Meta:
        model = Municipality
        fields = [
            'name', 'province', 'region', 'population', 'area_sqkm',
            'contact_name', 'contact_email', 'contact_phone', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'province': forms.TextInput(attrs={'class': 'form-control'}),
            'region': forms.TextInput(attrs={'class': 'form-control'}),
            'population': forms.NumberInput(attrs={'class': 'form-control'}),
            'area_sqkm': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_phone': forms.TextInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SubProjectForm(forms.ModelForm):
    """Form per la gestione dei sottoprogetti."""
    
    class Meta:
        model = SubProject
        fields = [
            'project', 'municipality', 'name', 'description', 'status',
            'start_date', 'planned_completion_date', 'actual_completion_date',
            'budget', 'responsible_person'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-control'}),
            'municipality': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'planned_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actual_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'responsible_person': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        planned_completion_date = cleaned_data.get('planned_completion_date')
        actual_completion_date = cleaned_data.get('actual_completion_date')
        
        if start_date and planned_completion_date and planned_completion_date < start_date:
            raise forms.ValidationError(
                "La data di completamento pianificata non può essere precedente alla data di inizio."
            )
        
        if start_date and actual_completion_date and actual_completion_date < start_date:
            raise forms.ValidationError(
                "La data di completamento effettiva non può essere precedente alla data di inizio."
            )
        
        return cleaned_data

class ChargingStationForm(forms.ModelForm):
    """Form per la gestione delle stazioni di ricarica."""
    
    class Meta:
        model = ChargingStation
        fields = [
            'subproject', 'name', 'identifier', 'station_type', 'status', 'address', 
            'latitude', 'longitude', 'installation_date', 'activation_date',
            'connection_cost', 'installation_cost', 'station_cost', 'design_cost',
            'permit_cost', 'other_costs', 'power_kw', 'connector_types', 
            'num_connectors', 'grid_connection_capacity', 'notes'
        ]
        widgets = {
            'subproject': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'identifier': forms.TextInput(attrs={'class': 'form-control'}),
            'station_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'activation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'connection_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'station_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'design_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'permit_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'other_costs': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'power_kw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'connector_types': forms.TextInput(attrs={'class': 'form-control'}),
            'num_connectors': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'grid_connection_capacity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SolarInstallationForm(forms.ModelForm):
    """Form per la gestione degli impianti fotovoltaici."""
    
    class Meta:
        model = SolarInstallation
        fields = [
            'charging_station', 'capacity_kw', 'panel_type', 'num_panels',
            'installation_cost', 'annual_production_kwh', 'installation_date', 'notes'
        ]
        widgets = {
            'charging_station': forms.Select(attrs={'class': 'form-control'}),
            'capacity_kw': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'panel_type': forms.TextInput(attrs={'class': 'form-control'}),
            'num_panels': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'installation_cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'annual_production_kwh': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'installation_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
