# mapping/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from cpo_planner.projects.models import Project, SubProject, ChargingStation
from .models import MapSettings, CustomMarker, SavedMap

class MapSettingsForm(forms.ModelForm):
    """Form per le impostazioni della mappa"""
    class Meta:
        model = MapSettings
        fields = [
            'name', 'description', 'default_center_lat', 'default_center_lng',
            'default_zoom', 'map_style', 'show_clusters', 'min_cluster_size',
            'show_planned', 'show_under_construction', 'show_operational',
            'min_power', 'max_power', 'is_default'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'default_center_lat': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'default_center_lng': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'default_zoom': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 18}),
            'map_style': forms.Select(attrs={'class': 'form-control'}),
            'show_clusters': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_cluster_size': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'max': 10}),
            'show_planned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_under_construction': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_operational': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'min_power': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'max_power': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        settings = super().save(commit=False)
        
        if self.user and not settings.pk:
            settings.created_by = self.user
            
        if commit:
            settings.save()
            
        return settings

class CustomMarkerForm(forms.ModelForm):
    """Form per i marker personalizzati"""
    class Meta:
        model = CustomMarker
        fields = [
            'name', 'description', 'latitude', 'longitude',
            'color', 'icon', 'is_visible', 'popup_title',
            'popup_content', 'project', 'subproject'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.000001'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'icon': forms.Select(attrs={'class': 'form-control'}),
            'is_visible': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'popup_title': forms.TextInput(attrs={'class': 'form-control'}),
            'popup_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'project': forms.Select(attrs={'class': 'form-control'}),
            'subproject': forms.Select(attrs={'class': 'form-control'})
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtra i sotto-progetti in base al progetto selezionato
        if self.instance and self.instance.project:
            self.fields['subproject'].queryset = SubProject.objects.filter(project=self.instance.project)
        else:
            self.fields['subproject'].queryset = SubProject.objects.none()
    
    def save(self, commit=True):
        marker = super().save(commit=False)
        
        if self.user and not marker.pk:
            marker.created_by = self.user
            
        if commit:
            marker.save()
            
        return marker

class SavedMapForm(forms.ModelForm):
    """Form per salvare una mappa"""
    class Meta:
        model = SavedMap
        fields = [
            'name', 'description', 'center_lat', 'center_lng',
            'zoom', 'is_public'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'center_lat': forms.HiddenInput(),
            'center_lng': forms.HiddenInput(),
            'zoom': forms.HiddenInput(),
            'is_public': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
    
    # Campi aggiuntivi per i dati JSON dei filtri
    filters_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    # Campi per gestire le relazioni many-to-many
    charging_station_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    project_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    subproject_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    custom_marker_ids = forms.CharField(
        widget=forms.HiddenInput(),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        saved_map = super().save(commit=False)
        
        # Imposta l'utente
        if self.user and not saved_map.pk:
            saved_map.created_by = self.user
        
        # Salva i filtri come JSON
        if 'filters_json' in self.cleaned_data and self.cleaned_data['filters_json']:
            try:
                import json
                saved_map.filters = json.loads(self.cleaned_data['filters_json'])
            except:
                saved_map.filters = {}
        
        if commit:
            saved_map.save()
            
            # Gestisci le relazioni many-to-many
            if 'charging_station_ids' in self.cleaned_data and self.cleaned_data['charging_station_ids']:
                station_ids = self.cleaned_data['charging_station_ids'].split(',')
                stations = ChargingStation.objects.filter(id__in=station_ids)
                saved_map.charging_stations.set(stations)
            
            if 'project_ids' in self.cleaned_data and self.cleaned_data['project_ids']:
                project_ids = self.cleaned_data['project_ids'].split(',')
                projects = Project.objects.filter(id__in=project_ids)
                saved_map.projects.set(projects)
            
            if 'subproject_ids' in self.cleaned_data and self.cleaned_data['subproject_ids']:
                subproject_ids = self.cleaned_data['subproject_ids'].split(',')
                subprojects = SubProject.objects.filter(id__in=subproject_ids)
                saved_map.subprojects.set(subprojects)
            
            if 'custom_marker_ids' in self.cleaned_data and self.cleaned_data['custom_marker_ids']:
                marker_ids = self.cleaned_data['custom_marker_ids'].split(',')
                markers = CustomMarker.objects.filter(id__in=marker_ids)
                saved_map.custom_markers.set(markers)
            
        return saved_map

class MapFilterForm(forms.Form):
    """Form per filtrare le stazioni sulla mappa"""
    # Filtri di status
    status = forms.MultipleChoiceField(
        label=_('Stato'),
        choices=[
            ('planned', _('Pianificata')),
            ('under_construction', _('In Costruzione')),
            ('operational', _('Operativa')),
            ('maintenance', _('In Manutenzione')),
            ('offline', _('Non Operativa')),
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    # Filtri di potenza
    min_power = forms.FloatField(
        label=_('Potenza Minima (kW)'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0'})
    )
    
    max_power = forms.FloatField(
        label=_('Potenza Massima (kW)'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0'})
    )
    
    # Filtri per progetto
    project = forms.ModelChoiceField(
        label=_('Progetto'),
        queryset=Project.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Filtri per sotto-progetto
    subproject = forms.ModelChoiceField(
        label=_('Sotto-progetto'),
        queryset=SubProject.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Filtri per numero minimo di connettori
    min_connectors = forms.IntegerField(
        label=_('Connettori Minimi'),
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '1'})
    )
    
    # Opzioni di visualizzazione
    show_clusters = forms.BooleanField(
        label=_('Mostra Cluster'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    show_custom_markers = forms.BooleanField(
        label=_('Mostra Marker Personalizzati'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Imposta valori iniziali predefiniti basati su MapSettings
        map_settings = MapSettings.get_default()
        if map_settings:
            status_choices = []
            if map_settings.show_planned:
                status_choices.append('planned')
            if map_settings.show_under_construction:
                status_choices.append('under_construction')
            if map_settings.show_operational:
                status_choices.append('operational')
            
            self.fields['status'].initial = status_choices
            self.fields['min_power'].initial = map_settings.min_power
            self.fields['max_power'].initial = map_settings.max_power
            self.fields['show_clusters'].initial = map_settings.show_clusters

class SavedMapFilterForm(forms.Form):
    """Form per filtrare le mappe salvate"""
    search = forms.CharField(
        label=_('Cerca'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Cerca per nome o descrizione')
        })
    )
    
    user = forms.ModelChoiceField(
        label=_('Utente'),
        queryset=None,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    is_public = forms.ChoiceField(
        label=_('Visibilità'),
        choices=[
            ('', _('Tutti')),
            ('1', _('Pubblici')),
            ('0', _('Privati')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Imposta il queryset per gli utenti con mappe salvate
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.fields['user'].queryset = User.objects.filter(saved_maps__isnull=False).distinct()