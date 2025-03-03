# mapping/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.serializers import serialize

from cpo_planner.projects.models import Project, SubProject, ChargingStation
from .models import MapSettings, CustomMarker, SavedMap
from .forms import (
    MapSettingsForm, CustomMarkerForm, SavedMapForm,
    MapFilterForm, SavedMapFilterForm
)

class MapView(LoginRequiredMixin, TemplateView):
    """Vista principale della mappa interattiva"""
    template_name = 'mapping/map.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ottieni le impostazioni predefinite della mappa
        map_settings = MapSettings.get_default()
        if not map_settings:
            # Create default settings if none exist
            try:
                map_settings = MapSettings.objects.create(
                    name=_('Impostazioni Predefinite'),
                    is_default=True,
                    created_by=self.request.user
                )
            except:
                # Fallback to hardcoded defaults
                map_settings = MapSettings(
                    default_center_lat=41.9028,
                    default_center_lng=12.4964,
                    default_zoom=6
                )
        
        context['map_settings'] = map_settings
        
        # Prepara filtri
        context['filter_form'] = MapFilterForm()
        
        # Aggiungi conteggio totale stazioni
        context['total_stations'] = ChargingStation.objects.count()
        context['operational_stations'] = ChargingStation.objects.filter(status='operational').count()
        
        # Aggiungi marker personalizzati pubblici
        context['custom_markers'] = CustomMarker.objects.filter(is_visible=True).count()
        
        # Se è passato un ID di un progetto, filtra solo le stazioni di quel progetto
        project_id = self.kwargs.get('project_id')
        if project_id:
            context['project'] = get_object_or_404(Project, id=project_id)
            context['filtered_by_project'] = True
        
        # Se è passato un ID di un sotto-progetto, filtra solo le stazioni di quel sotto-progetto
        subproject_id = self.kwargs.get('subproject_id')
        if subproject_id:
            context['subproject'] = get_object_or_404(SubProject, id=subproject_id)
            context['filtered_by_subproject'] = True
        
        # Se è specificato un ID di mappa salvata, carica quella mappa
        saved_map_id = self.kwargs.get('map_id')
        if saved_map_id:
            context['saved_map'] = get_object_or_404(
                SavedMap.objects.filter(
                    Q(created_by=self.request.user) | Q(is_public=True)
                ),
                id=saved_map_id
            )
        
        # Aggiungi API key per Mapbox
        from django.conf import settings
        context['mapbox_api_key'] = getattr(settings, 'MAPBOX_API_KEY', '')
        
        return context

class MapSettingsListView(LoginRequiredMixin, ListView):
    """Vista per elencare le impostazioni della mappa"""
    model = MapSettings
    template_name = 'mapping/settings_list.html'
    context_object_name = 'settings_list'
    
    def get_queryset(self):
        return MapSettings.objects.all().order_by('-is_default', '-created_at')

class MapSettingsCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista per creare nuove impostazioni della mappa"""
    model = MapSettings
    form_class = MapSettingsForm
    template_name = 'mapping/settings_form.html'
    permission_required = 'mapping.add_mapsettings'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Impostazioni della mappa create con successo.'))
        return response
    
    def get_success_url(self):
        return reverse('mapping:settings_list')

class MapSettingsUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista per aggiornare le impostazioni della mappa"""
    model = MapSettings
    form_class = MapSettingsForm
    template_name = 'mapping/settings_form.html'
    permission_required = 'mapping.change_mapsettings'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Impostazioni della mappa aggiornate con successo.'))
        return response
    
    def get_success_url(self):
        return reverse('mapping:settings_list')

class MapSettingsDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista per eliminare le impostazioni della mappa"""
    model = MapSettings
    template_name = 'mapping/settings_confirm_delete.html'
    permission_required = 'mapping.delete_mapsettings'
    success_url = reverse_lazy('mapping:settings_list')
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Impostazioni della mappa eliminate con successo.'))
        return response

class CustomMarkerListView(LoginRequiredMixin, ListView):
    """Vista per elencare i marker personalizzati"""
    model = CustomMarker
    template_name = 'mapping/marker_list.html'
    context_object_name = 'markers'
    
    def get_queryset(self):
        # Mostra solo i marker dell'utente e quelli pubblici
        return CustomMarker.objects.filter(
            Q(created_by=self.request.user) | Q(is_visible=True)
        ).order_by('-created_at')

class CustomMarkerCreateView(LoginRequiredMixin, CreateView):
    """Vista per creare nuovi marker personalizzati"""
    model = CustomMarker
    form_class = CustomMarkerForm
    template_name = 'mapping/marker_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Marker personalizzato creato con successo.'))
        return response
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Se sono specificate coordinate nell'URL, le usa come valori iniziali
        lat = self.request.GET.get('lat')
        lng = self.request.GET.get('lng')
        
        if lat and lng:
            try:
                initial['latitude'] = float(lat)
                initial['longitude'] = float(lng)
            except ValueError:
                pass
        
        # Se è specificato un progetto nell'URL, lo usa come valore iniziale
        project_id = self.request.GET.get('project')
        if project_id:
            try:
                initial['project'] = Project.objects.get(id=project_id)
            except Project.DoesNotExist:
                pass
        
        # Se è specificato un sotto-progetto nell'URL, lo usa come valore iniziale
        subproject_id = self.request.GET.get('subproject')
        if subproject_id:
            try:
                initial['subproject'] = SubProject.objects.get(id=subproject_id)
            except SubProject.DoesNotExist:
                pass
                
        return initial
    
    def get_success_url(self):
        return reverse('mapping:marker_list')

class CustomMarkerUpdateView(LoginRequiredMixin, UpdateView):
    """Vista per aggiornare i marker personalizzati"""
    model = CustomMarker
    form_class = CustomMarkerForm
    template_name = 'mapping/marker_form.html'
    
    def get_queryset(self):
        # Consenti la modifica solo dei propri marker
        return CustomMarker.objects.filter(created_by=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Marker personalizzato aggiornato con successo.'))
        return response
    
    def get_success_url(self):
        return reverse('mapping:marker_list')

class CustomMarkerDeleteView(LoginRequiredMixin, DeleteView):
    """Vista per eliminare i marker personalizzati"""
    model = CustomMarker
    template_name = 'mapping/marker_confirm_delete.html'
    
    def get_queryset(self):
        # Consenti l'eliminazione solo dei propri marker
        return CustomMarker.objects.filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Marker personalizzato eliminato con successo.'))
        return response
    
    def get_success_url(self):
        return reverse('mapping:marker_list')

class SavedMapListView(LoginRequiredMixin, ListView):
    """Vista per elencare le mappe salvate"""
    model = SavedMap
    template_name = 'mapping/saved_map_list.html'
    context_object_name = 'saved_maps'
    paginate_by = 10
    
    def get_queryset(self):
        # Mostra le mappe salvate dell'utente e le mappe pubbliche
        queryset = SavedMap.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        )
        
        # Applica filtri
        form = SavedMapFilterForm(self.request.GET)
        if form.is_valid():
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | 
                    Q(description__icontains=search)
                )
            
            user = form.cleaned_data.get('user')
            if user:
                queryset = queryset.filter(created_by=user)
            
            is_public = form.cleaned_data.get('is_public')
            if is_public == '1':
                queryset = queryset.filter(is_public=True)
            elif is_public == '0':
                queryset = queryset.filter(is_public=False, created_by=self.request.user)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = SavedMapFilterForm(self.request.GET)
        return context

class SavedMapCreateView(LoginRequiredMixin, CreateView):
    """Vista per salvare una nuova mappa"""
    model = SavedMap
    form_class = SavedMapForm
    template_name = 'mapping/saved_map_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Mappa salvata con successo.'))
        return response
    
    def get_success_url(self):
        return reverse('mapping:map_view', kwargs={'map_id': self.object.pk})

class SavedMapUpdateView(LoginRequiredMixin, UpdateView):
    """Vista per aggiornare una mappa salvata"""
    model = SavedMap
    form_class = SavedMapForm
    template_name = 'mapping/saved_map_form.html'
    
    def get_queryset(self):
        # Consenti la modifica solo delle proprie mappe
        return SavedMap.objects.filter(created_by=self.request.user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Mappa aggiornata con successo.'))
        return response
    
    def get_initial(self):
        initial = super().get_initial()
        saved_map = self.get_object()
        
        # Converti le relazioni in stringhe di ID separati da virgole
        if saved_map:
            station_ids = [str(station.id) for station in saved_map.charging_stations.all()]
            initial['charging_station_ids'] = ','.join(station_ids)
            
            project_ids = [str(project.id) for project in saved_map.projects.all()]
            initial['project_ids'] = ','.join(project_ids)
            
            subproject_ids = [str(subproject.id) for subproject in saved_map.subprojects.all()]
            initial['subproject_ids'] = ','.join(subproject_ids)
            
            marker_ids = [str(marker.id) for marker in saved_map.custom_markers.all()]
            initial['custom_marker_ids'] = ','.join(marker_ids)
            
            # Converti i filtri in JSON
            if saved_map.filters:
                import json
                initial['filters_json'] = json.dumps(saved_map.filters)
        
        return initial
    
    def get_success_url(self):
        return reverse('mapping:map_view', kwargs={'map_id': self.object.pk})

class SavedMapDeleteView(LoginRequiredMixin, DeleteView):
    """Vista per eliminare una mappa salvata"""
    model = SavedMap
    template_name = 'mapping/saved_map_confirm_delete.html'
    
    def get_queryset(self):
        # Consenti l'eliminazione solo delle proprie mappe
        return SavedMap.objects.filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, _('Mappa eliminata con successo.'))
        return response
    
    def get_success_url(self):
        return reverse('mapping:saved_map_list')

@login_required
def get_stations_geojson(request):
    """API per ottenere i dati GeoJSON delle stazioni di ricarica"""
    # Ottieni parametri di filtro
    status = request.GET.getlist('status[]', None)
    min_power = request.GET.get('min_power', None)
    max_power = request.GET.get('max_power', None)
    project_id = request.GET.get('project', None)
    subproject_id = request.GET.get('subproject', None)
    min_connectors = request.GET.get('min_connectors', None)
    
    # Base queryset
    queryset = ChargingStation.objects.all()
    
    # Applica filtri
    if status:
        queryset = queryset.filter(status__in=status)
    
    if min_power:
        try:
            queryset = queryset.filter(power__gte=float(min_power))
        except (ValueError, TypeError):
            pass
    
    if max_power:
        try:
            queryset = queryset.filter(power__lte=float(max_power))
        except (ValueError, TypeError):
            pass
    
    if project_id:
        try:
            queryset = queryset.filter(subproject__project_id=int(project_id))
        except (ValueError, TypeError):
            pass
    
    if subproject_id:
        try:
            queryset = queryset.filter(subproject_id=int(subproject_id))
        except (ValueError, TypeError):
            pass
    
    if min_connectors:
        try:
            queryset = queryset.filter(connectors__gte=int(min_connectors))
        except (ValueError, TypeError):
            pass
    
    # Ottieni solo le stazioni con coordinate valide
    queryset = queryset.filter(latitude__isnull=False, longitude__isnull=False)
    
    # Prepara la risposta GeoJSON
    features = []
    for station in queryset:
        # Crea le proprietà per il popup
        properties = {
            'id': station.id,
            'name': station.name,
            'location': station.location,
            'address': station.address,
            'status': station.status,
            'status_display': station.get_status_display(),
            'power': station.power,
            'connectors': station.connectors,
            'charging_points': station.charging_points,
            'installation_date': station.installation_date.strftime('%d/%m/%Y') if station.installation_date else None,
            'subproject_id': station.subproject_id if station.subproject else None,
            'subproject_name': station.subproject.name if station.subproject else None,
            'project_id': station.subproject.project_id if station.subproject and station.subproject.project else None,
            'project_name': station.subproject.project.name if station.subproject and station.subproject.project else None,
        }
        
        # Crea il feature GeoJSON
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [station.longitude, station.latitude]
            },
            'properties': properties
        }
        
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return JsonResponse(geojson)

@login_required
def get_custom_markers_geojson(request):
    """API per ottenere i dati GeoJSON dei marker personalizzati"""
    # Base queryset - solo marker visibili e creati dall'utente
    queryset = CustomMarker.objects.filter(
        Q(is_visible=True) | Q(created_by=request.user)
    )
    
    # Filtra per progetto se specificato
    project_id = request.GET.get('project', None)
    if project_id:
        try:
            queryset = queryset.filter(Q(project_id=int(project_id)) | Q(subproject__project_id=int(project_id)))
        except (ValueError, TypeError):
            pass
    
    # Filtra per sotto-progetto se specificato
    subproject_id = request.GET.get('subproject', None)
    if subproject_id:
        try:
            queryset = queryset.filter(subproject_id=int(subproject_id))
        except (ValueError, TypeError):
            pass
    
    # Prepara la risposta GeoJSON
    features = []
    for marker in queryset:
        # Crea le proprietà per il popup
        properties = {
            'id': marker.id,
            'name': marker.name,
            'description': marker.description,
            'color': marker.color,
            'icon': marker.icon,
            'popup_title': marker.popup_title,
            'popup_content': marker.popup_content,
            'project_id': marker.project_id if marker.project else None,
            'project_name': marker.project.name if marker.project else None,
            'subproject_id': marker.subproject_id if marker.subproject else None,
            'subproject_name': marker.subproject.name if marker.subproject else None,
            'created_by': marker.created_by.get_full_name(),
            'is_own_marker': marker.created_by_id == request.user.id
        }
        
        # Crea il feature GeoJSON
        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [marker.longitude, marker.latitude]
            },
            'properties': properties
        }
        
        features.append(feature)
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    return JsonResponse(geojson)

@login_required
def get_saved_map_data(request, map_id):
    """API per ottenere i dati di una mappa salvata"""
    saved_map = get_object_or_404(
        SavedMap.objects.filter(
            Q(created_by=request.user) | Q(is_public=True)
        ),
        id=map_id
    )
    
    # Prepara i dati della mappa
    map_data = {
        'id': saved_map.id,
        'name': saved_map.name,
        'description': saved_map.description,
        'center': {
            'lat': saved_map.center_lat,
            'lng': saved_map.center_lng
        },
        'zoom': saved_map.zoom,
        'filters': saved_map.filters,
        'is_public': saved_map.is_public,
        'created_by': saved_map.created_by.get_full_name(),
        'is_own_map': saved_map.created_by_id == request.user.id,
        'created_at': saved_map.created_at.strftime('%d/%m/%Y %H:%M'),
        'charging_stations': [station.id for station in saved_map.charging_stations.all()],
        'projects': [project.id for project in saved_map.projects.all()],
        'subprojects': [subproject.id for subproject in saved_map.subprojects.all()],
        'custom_markers': [marker.id for marker in saved_map.custom_markers.all()]
    }
    
    return JsonResponse(map_data)