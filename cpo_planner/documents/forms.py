# documents/forms.py
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from cpo_planner.projects.models import Project, SubProject, ChargingStation
from .models import Document, DocumentCategory, DocumentNote, DocumentTask, ProjectDocument, DocumentTemplate
class DocumentForm(forms.ModelForm):
    """Form per la creazione e modifica dei documenti"""
    
    # Campo per selezionare il tipo di entità
    entity_type = forms.ChoiceField(
        label=_('Tipo di Entità'),
        choices=[
            ('project', _('Progetto')),
            ('subproject', _('Sotto-progetto')),
            ('chargingstation', _('Stazione di ricarica')),
        ],
        widget=forms.RadioSelect,
        initial='project'
    )
    
    # Campi dinamici per selezionare l'entità specifica
    project = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        label=_('Progetto'),
        required=False
    )
    
    subproject = forms.ModelChoiceField(
        queryset=SubProject.objects.all(),
        label=_('Sotto-progetto'),
        required=False
    )
    
    chargingstation = forms.ModelChoiceField(
        queryset=ChargingStation.objects.all(),
        label=_('Stazione di ricarica'),
        required=False
    )
    
    class Meta:
        model = Document
        fields = [
            'title', 'description', 'file', 'category', 'version', 
            'status', 'issue_date', 'expiry_date'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'issue_date': forms.DateInput(attrs={'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        entity_obj = kwargs.pop('entity_obj', None)
        entity_type = kwargs.pop('entity_type', None)
        
        super().__init__(*args, **kwargs)
        
        # Se è un'istanza esistente, precompila i campi dell'entità
        if self.instance.pk:
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
        
        # Se è specificata un'entità, precompila i campi relativi
        if entity_obj and entity_type:
            self.fields['entity_type'].initial = entity_type
            self.fields[entity_type].initial = entity_obj.id
            # Limita le scelte alle entità pertinenti
            if entity_type == 'project':
                self.fields['subproject'].queryset = SubProject.objects.filter(project=entity_obj)
                self.fields['chargingstation'].queryset = ChargingStation.objects.filter(subproject__project=entity_obj)
            elif entity_type == 'subproject':
                self.fields['project'].initial = entity_obj.project.id
                self.fields['chargingstation'].queryset = ChargingStation.objects.filter(subproject=entity_obj)
                
        # Aggiungi classi CSS per lo stile
        for field_name, field in self.fields.items():
            if field_name not in ['entity_type']:
                field.widget.attrs.update({'class': 'form-control'})
    
    def clean(self):
        cleaned_data = super().clean()
        entity_type = cleaned_data.get('entity_type')
        
        # Verifica che sia selezionata un'entità del tipo corretto
        entity_obj = None
        if entity_type == 'project':
            entity_obj = cleaned_data.get('project')
        elif entity_type == 'subproject':
            entity_obj = cleaned_data.get('subproject')
        elif entity_type == 'chargingstation':
            entity_obj = cleaned_data.get('chargingstation')
        
        if not entity_obj:
            raise forms.ValidationError(_('Seleziona un\'entità valida per associare il documento.'))
            
        return cleaned_data
    
    def save(self, commit=True):
        document = super().save(commit=False)
        
        # Imposta il content_type e object_id in base all'entità selezionata
        entity_type = self.cleaned_data.get('entity_type')
        if entity_type == 'project':
            entity_obj = self.cleaned_data.get('project')
            content_type = ContentType.objects.get_for_model(Project)
        elif entity_type == 'subproject':
            entity_obj = self.cleaned_data.get('subproject')
            content_type = ContentType.objects.get_for_model(SubProject)
        elif entity_type == 'chargingstation':
            entity_obj = self.cleaned_data.get('chargingstation')
            content_type = ContentType.objects.get_for_model(ChargingStation)
        
        document.content_type = content_type
        document.object_id = entity_obj.id
        
        # Imposta l'utente creatore
        if self.user and not document.pk:
            document.created_by = self.user
            
        if commit:
            document.save()
            
        return document

class DocumentNoteForm(forms.ModelForm):
    """Form per aggiungere note ai documenti"""
    class Meta:
        model = DocumentNote
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        }

class DocumentTaskForm(forms.ModelForm):
    """Form per creare attività legate ai documenti"""
    class Meta:
        model = DocumentTask
        fields = ['title', 'description', 'status', 'assigned_to', 'due_date']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

class DocumentFilterForm(forms.Form):
    """Form per filtrare i documenti nella lista documenti"""
    category = forms.ModelChoiceField(
        queryset=DocumentCategory.objects.all(),
        required=False,
        empty_label=_("Tutte le categorie"),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    status = forms.ChoiceField(
        choices=[('', _('Tutti gli stati'))] + list(Document.status.field.choices),
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

class DocumentCategoryForm(forms.ModelForm):
    """Form per gestire le categorie di documenti"""
    class Meta:
        model = DocumentCategory
        fields = ['name', 'description', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ProjectDocumentForm(forms.ModelForm):
    """Form per i documenti specifici dei progetti"""
    class Meta:
        model = ProjectDocument
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'file': forms.FileInput(attrs={'class': 'form-control'})
        }