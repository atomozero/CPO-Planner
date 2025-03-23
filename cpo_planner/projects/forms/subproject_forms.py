# cpo_planner/projects/forms/subproject_forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
# Importa modelli consolidati
from cpo_core.models.subproject import SubProject, StationImage
from cpo_core.models.municipality import Municipality
from infrastructure.models import StationUsageProfile

class SubProjectForm(forms.ModelForm):
    # Sovrascrivi i campi di coordinate per accettare valori con virgola
    latitude_proposed = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False,
        label=_("Latitudine Proposta"),
        help_text=_("Usa il formato con punto decimale (es. 45.420930)")
    )
    longitude_proposed = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False,
        label=_("Longitudine Proposta"),
        help_text=_("Usa il formato con punto decimale (es. 12.123456)")
    )
    latitude_approved = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False,
        label=_("Latitudine Approvata"),
        help_text=_("Usa il formato con punto decimale (es. 45.420930)")
    )
    longitude_approved = forms.DecimalField(
        max_digits=9, decimal_places=6, required=False,
        label=_("Longitudine Approvata"),
        help_text=_("Usa il formato con punto decimale (es. 12.123456)")
    )
    
    class Meta:
        model = SubProject
        fields = [
            # Informazioni base
            'name', 'description', 'address', 'cadastral_data',
            'latitude_proposed', 'longitude_proposed',
            'latitude_approved', 'longitude_approved',
            
            # Giorni di indisponibilità
            'weekly_market_day', 'local_festival_days', 'rainy_days',  # Aggiunto rainy_days
            
            # Specifiche tecniche
            'charger_brand', 'charger_model', 'power_kw', 'power_requested',
            'connector_types', 'num_connectors', 'num_chargers', 'usage_profile',
            'ground_area_sqm',
            
            # Date
            'start_date', 'planned_completion_date', 'use_project_completion_date',
            
            # Costi dettagliati
            'equipment_cost', 'installation_cost', 'connection_cost',
            'permit_cost', 'modem_4g_cost', 'other_costs',
            
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
            'weekly_market_day': forms.Select(attrs={'class': 'form-control'}),
            'local_festival_days': forms.NumberInput(attrs={'min': '0', 'max': '60'}),
            'rainy_days': forms.NumberInput(attrs={'min': '0', 'max': '200'}),  # Widget per giorni di pioggia
            'budget': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'expected_revenue': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'roi': forms.NumberInput(attrs={'readonly': 'readonly'}),
            'power_kw': forms.NumberInput(attrs={'step': '0.1'}),
            'ground_area_sqm': forms.NumberInput(attrs={'step': '0.01'}),
            'equipment_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'installation_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'connection_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'permit_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'modem_4g_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'other_costs': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }
        
    # Campo nascosto per il project
    project = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    # Per ora rimuoviamo il campo delle immagini per risolvere il problema di migrazione
    # Lo implementeremo in seguito quando lavoreremo sul template
    
    def __init__(self, *args, **kwargs):
        self.project_id = kwargs.pop('project_id', None)
        
        # Debug della chiamata a __init__
        instance = kwargs.get('instance')
        if instance:
            print("DEBUG - __init__ SubProjectForm - received instance:", instance)
            print("DEBUG - __init__ SubProjectForm - instance values:", {
                'power_kw': instance.power_kw,
                'ground_area_sqm': instance.ground_area_sqm,
                'equipment_cost': instance.equipment_cost,
                'installation_cost': instance.installation_cost,
                'connection_cost': instance.connection_cost,
                'latitude_approved': instance.latitude_approved,
                'longitude_approved': instance.longitude_approved
            })
        
        super().__init__(*args, **kwargs)
        
        # Debug dei valori del campo dopo la creazione del form
        if instance:
            print("DEBUG - __init__ SubProjectForm - field values after form creation:", {
                'power_kw': self.fields['power_kw'].initial,
                'ground_area_sqm': self.fields['ground_area_sqm'].initial,
                'equipment_cost': self.fields['equipment_cost'].initial,
                'installation_cost': self.fields['installation_cost'].initial,
                'connection_cost': self.fields['connection_cost'].initial,
                'latitude_approved': self.fields['latitude_approved'].initial,
                'longitude_approved': self.fields['longitude_approved'].initial
            })
            
            # Imposta manualmente i valori iniziali dai valori dell'istanza
            self.initial['power_kw'] = instance.power_kw
            self.initial['ground_area_sqm'] = instance.ground_area_sqm
            self.initial['equipment_cost'] = instance.equipment_cost
            self.initial['installation_cost'] = instance.installation_cost
            self.initial['connection_cost'] = instance.connection_cost
            self.initial['permit_cost'] = instance.permit_cost
            self.initial['modem_4g_cost'] = instance.modem_4g_cost
            self.initial['other_costs'] = instance.other_costs
            
            # Imposta valori di coordinate anche con stringformat per assicurarsi che il formato sia corretto
            if instance.latitude_proposed:
                self.initial['latitude_proposed'] = instance.latitude_proposed
            if instance.longitude_proposed:
                self.initial['longitude_proposed'] = instance.longitude_proposed
            if instance.latitude_approved:
                self.initial['latitude_approved'] = instance.latitude_approved
            if instance.longitude_approved:
                self.initial['longitude_approved'] = instance.longitude_approved
        
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
        
        # Aggiungi help text per il campo rainy_days
        self.fields['rainy_days'].help_text = _(
            "Giorni di pioggia stimati all'anno. L'utilizzo delle colonnine in questi giorni "
            "è ridotto del 30% rispetto a un giorno normale."
        )
        
        # Nascondi il campo municipality dal form, verrà popolato automaticamente nella view
        if 'municipality' in self.fields:
            del self.fields['municipality']