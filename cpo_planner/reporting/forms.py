# reporting/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.forms import inlineformset_factory

from projects.models.project import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.charging_station import ChargingStation
from .models import (
    ReportTemplate, TemplatePlaceholder, Report, 
    ReportPlaceholderValue, ReportType
)

class ReportTemplateForm(forms.ModelForm):
    """Form per la creazione e modifica dei template di report"""
    class Meta:
        model = ReportTemplate
        fields = [
            'name', 'description', 'type', 'template_file', 
            'css', 'is_default'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
            'template_file': forms.FileInput(attrs={'class': 'form-control-file'}),
            'css': forms.Textarea(attrs={
                'rows': 5, 
                'class': 'form-control',
                'placeholder': _('CSS aggiuntivo per template HTML')
            }),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
    def save(self, commit=True):
        template = super().save(commit=False)
        
        if self.user and not template.pk:
            template.created_by = self.user
            
        if commit:
            template.save()
            
        return template

class TemplatePlaceholderForm(forms.ModelForm):
    """Form per i segnaposti nei template"""
    class Meta:
        model = TemplatePlaceholder
        fields = ['name', 'description', 'default_value']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            'default_value': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'})
        }

# FormSet per gestire multiple istanze di TemplatePlaceholder
TemplatePlaceholderFormSet = inlineformset_factory(
    ReportTemplate, 
    TemplatePlaceholder,
    form=TemplatePlaceholderForm,
    extra=1,
    can_delete=True
)

class ReportForm(forms.ModelForm):
    """Form per la creazione di report"""
    
    # Campo per selezionare il tipo di entità
    entity_type = forms.ChoiceField(
        label=_('Tipo di Entità'),
        choices=[
            ('', _('Nessuna entità')),
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
    
    # Per la selezione del template
    report_type = forms.ChoiceField(
        label=_('Tipo di Report'),
        choices=ReportType.choices,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Report
        fields = ['title', 'description', 'template']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'template': forms.Select(attrs={'class': 'form-control'})
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Imposta il queryset iniziale per il template
        self.fields['template'].queryset = ReportTemplate.objects.all()
        
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
            
            # Imposta il tipo di report in base al template selezionato
            if self.instance.template:
                self.fields['report_type'].initial = self.instance.template.type
        
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
        
        # Verifica che il template sia compatibile con il tipo di report
        report_type = cleaned_data.get('report_type')
        template = cleaned_data.get('template')
        
        if report_type and template and template.type != report_type:
            raise forms.ValidationError(_(
                'Il template selezionato non è compatibile con il tipo di report scelto.'
            ))
            
        return cleaned_data
    
    def save(self, commit=True):
        report = super().save(commit=False)
        
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
            
            report.content_type = content_type
            report.object_id = entity_obj.id
        else:
            report.content_type = None
            report.object_id = None
        
        # Imposta l'utente creatore
        if self.user and not report.pk:
            report.created_by = self.user
            
        if commit:
            report.save()
            
        return report

class PlaceholderValueForm(forms.ModelForm):
    """Form per i valori dei segnaposti nei report"""
    class Meta:
        model = ReportPlaceholderValue
        fields = ['value']
        widgets = {
            'value': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
        }

class ReportFilterForm(forms.Form):
    """Form per filtrare i report nella lista"""
    report_type = forms.ChoiceField(
        choices=[('', _('Tutti i tipi'))] + list(ReportType.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Cerca per titolo o descrizione...')
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
