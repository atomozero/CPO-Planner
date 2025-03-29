# cpo_planner/projects/forms/project_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
# Importa il modello consolidato
from cpo_core.models.project import Project
# Importa Municipality da infrastructure invece di cpo_core
from infrastructure.models import Municipality
from datetime import date

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'name', 'description', 'region', 'municipality', 'start_date', 
            'expected_completion_date', 'total_budget', 
            'total_expected_revenue', 'status', 'photovoltaic_integration',
            'logo'
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_completion_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'municipality': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendi region opzionale per test
        self.fields['region'].required = False
        
        # Configura il campo municipality con il queryset da Infrastructure
# Nel metodo __init__ o ovunque sia usato Comune
        self.fields['municipality'].queryset = Municipality.objects.all().order_by('name')
        self.fields['municipality'].required = False
        self.fields['municipality'].label = _("Comune principale")
        self.fields['municipality'].help_text = _("Seleziona il comune principale del progetto. I sottoprogetti erediteranno questo comune.")
        
        # Debug: mostra l'ID del comune selezionato nel form
        if self.instance and self.instance.pk and self.instance.municipality:
            print(f"DEBUG ProjectForm: Comune attuale per progetto {self.instance.id}: {self.instance.municipality.id} - {self.instance.municipality.name}")
        
        # Imposta valori predefiniti
        if not self.instance.pk:  # Solo per nuove istanze
            self.fields['status'].initial = 'planning'
            # Rimuoviamo il default 'Nord' per il campo regione
            self.fields['start_date'].initial = date.today()
            self.fields['expected_completion_date'].initial = date.today()
            self.fields['total_budget'].initial = 0
            self.fields['total_expected_revenue'].initial = 0
            
    def clean(self):
        cleaned_data = super().clean()
        
        # Assicurati che la regione sia impostata
        if not cleaned_data.get('region'):
            cleaned_data['region'] = 'Veneto'
            
        if not cleaned_data.get('start_date'):
            cleaned_data['start_date'] = date.today()
            
        if not cleaned_data.get('expected_completion_date'):
            cleaned_data['expected_completion_date'] = date.today()
            
        return cleaned_data