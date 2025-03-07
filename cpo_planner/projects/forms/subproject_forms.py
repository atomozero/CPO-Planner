# cpo_planner/projects/forms/subproject_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
# Importa modelli consolidati
from cpo_core.models.subproject import SubProject, StationImage
from cpo_core.models.municipality import Municipality
from infrastructure.models import StationUsageProfile

class SubProjectForm(forms.ModelForm):
    class Meta:
        model = SubProject
        fields = [
            # Informazioni base
            'name', 'description', 'address', 'cadastral_data',
            'latitude_proposed', 'longitude_proposed',
            'latitude_approved', 'longitude_approved',
            
            # Specifiche tecniche
            'charger_brand', 'charger_model', 'power_kw', 'power_requested',
            'connector_types', 'num_connectors', 'num_chargers', 'usage_profile',
            'ground_area_sqm',
            
            # Date
            'start_date', 'planned_completion_date', 'use_project_completion_date',
            
            # Costi dettagliati
            'equipment_cost', 'installation_cost', 'connection_cost',
            'permit_cost', 'civil_works_cost', 'other_costs',
            
            # Finanziari e stato
            'budget', 'expected_revenue', 'roi', 'status'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'planned_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'connector_types': forms.TextInput(attrs={'placeholder': 'Es. Type 2, CCS, CHAdeMO'}),
            'cadastral_data': forms.TextInput(attrs={'placeholder': 'Foglio, Particella, Subalterno'}),
            'usage_profile': forms.Select(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'expected_revenue': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'roi': forms.NumberInput(attrs={'readonly': 'readonly'}),
        }
        
    # Campo nascosto per il project
    project = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    # Per ora rimuoviamo il campo delle immagini per risolvere il problema di migrazione
    # Lo implementeremo in seguito quando lavoreremo sul template
    
    def __init__(self, *args, **kwargs):
        self.project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        # Popola i profili di utilizzo
        self.fields['usage_profile'].queryset = StationUsageProfile.objects.all().order_by('name')
        
        # Rendi i campi di ricavo e ROI non richiesti e di sola lettura
        self.fields['expected_revenue'].required = False
        self.fields['roi'].required = False
        self.fields['budget'].required = False
        
        # Rendi il campo planned_completion_date non richiesto se use_project_completion_date è selezionato
        self.fields['planned_completion_date'].required = False
        
        # Aggiungi note informative sui campi
        self.fields['power_requested'].help_text = _(
            "La potenza richiesta all'ente fornitore (solitamente E-Distribuzione). "
            "Il costo dell'allacciamento sarà calcolato automaticamente (80€ per kW)."
        )
        self.fields['use_project_completion_date'].help_text = _(
            "Se selezionato, verrà usata la data di completamento del progetto principale anziché "
            "specificare una data di completamento separata."
        )
        
        # Nascondi il campo municipality dal form, verrà popolato automaticamente nella view
        if 'municipality' in self.fields:
            del self.fields['municipality']