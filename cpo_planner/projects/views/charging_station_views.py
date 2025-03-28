# cpo_planner/projects/views/charging_station_views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.utils import timezone

from ..models.subproject import SubProject
from ..models.charging_station import ChargingStation
from ..models.photovoltaic import PhotovoltaicSystem
from ..forms.charging_station_forms import ChargingStationForm, ChargerForm, ChargingStationPhotoForm

# Import per le colonnine e foto
from cpo_core.models.subproject import Charger, SubProject as CoreSubProject
from cpo_core.models.charging_station import ChargingStationPhoto

# Aggiungi queste importazioni all'inizio del file, se non sono già presenti
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from infrastructure.models import UsageProfile

class ChargingStationDetailView(LoginRequiredMixin, DetailView):
    model = ChargingStation
    template_name = 'projects/charging_station_detail.html'
    context_object_name = 'station'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subproject'] = self.object.sub_project
        context['project'] = self.object.sub_project.project
        
        # Verifica se esiste un impianto fotovoltaico associato
        try:
            context['photovoltaic'] = self.object.photovoltaic_system
        except PhotovoltaicSystem.DoesNotExist:
            context['photovoltaic'] = None
            
        # Analisi finanziaria
        try:
            context['financial_analysis'] = self.object.financial_analysis
        except:
            context['financial_analysis'] = None
            
        # Cronoprogramma
        try:
            context['timeline'] = self.object.timeline
        except:
            context['timeline'] = None
        
        # Foto della stazione
        station_photos = ChargingStationPhoto.objects.filter(charging_station=self.object).order_by('-date_taken', '-created_at')
        context['station_photos'] = station_photos
        
        # Foto divise per fase
        context['pre_installation_photos'] = station_photos.filter(phase='pre_installation')
        context['during_installation_photos'] = station_photos.filter(phase='during_installation')
        context['post_installation_photos'] = station_photos.filter(phase='post_installation')
            
        return context

class ChargingStationCreateView(LoginRequiredMixin, CreateView):
    model = ChargingStation
    form_class = ChargingStationForm
    template_name = 'projects/charging_station_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        subproject_id = self.kwargs.get('subproject_id')
        context['subproject'] = get_object_or_404(SubProject, pk=subproject_id)
        context['project'] = context['subproject'].project
        context['title'] = _('Aggiungi Stazione di Ricarica')
        return context
    
    def form_valid(self, form):
        # Imposta il riferimento al sottoprogetto
        subproject_id = self.kwargs.get('subproject_id')
        form.instance.sub_project_id = subproject_id
        
        # Ottieni il sottoprogetto
        subproject = get_object_or_404(SubProject, pk=subproject_id)
        
        # Assicura che la stazione di ricarica usi lo stesso comune del sottoprogetto
        # In realtà questo non è necessario specificarlo esplicitamente dato che la stazione
        # di ricarica si riferisce solo al sottoprogetto e non ha un campo comune proprio
        
        messages.success(self.request, _('Stazione di ricarica creata con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        subproject = get_object_or_404(SubProject, pk=self.kwargs.get('subproject_id'))
        return reverse_lazy('projects:subproject_detail', kwargs={'pk': subproject.pk})

class ChargingStationUpdateView(LoginRequiredMixin, UpdateView):
    model = ChargingStation
    form_class = ChargingStationForm
    template_name = 'projects/charging_station_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subproject'] = self.object.sub_project
        context['project'] = self.object.sub_project.project
        context['title'] = _('Modifica Stazione di Ricarica')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Stazione di ricarica aggiornata con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:charging_station_detail', kwargs={'pk': self.object.pk})

class ChargingStationDeleteView(LoginRequiredMixin, DeleteView):
    model = ChargingStation
    template_name = 'projects/charging_station_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:subproject_detail', kwargs={'pk': self.object.sub_project.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Stazione di ricarica eliminata con successo!'))
        return super().delete(request, *args, **kwargs)

# Viste per la gestione delle colonnine singole
class ChargerListView(LoginRequiredMixin, ListView):
    """Vista per elencare tutte le colonnine di una stazione"""
    model = Charger
    template_name = 'projects/charger_list.html'
    context_object_name = 'chargers'
    
    def get_queryset(self):
        if 'subproject_id' in self.kwargs:
            self.subproject = get_object_or_404(CoreSubProject, pk=self.kwargs['subproject_id'])
            self.charging_station = None
            return Charger.objects.filter(subproject=self.subproject)
        elif 'charging_station_id' in self.kwargs:
            from cpo_core.models.charging_station import ChargingStation
            self.charging_station = get_object_or_404(ChargingStation, pk=self.kwargs['charging_station_id'])
            self.subproject = self.charging_station.subproject
            return Charger.objects.filter(charging_station=self.charging_station)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subproject'] = self.subproject
        
        if hasattr(self, 'charging_station') and self.charging_station:
            context['charging_station'] = self.charging_station
            context['page_title'] = f"Colonnine della stazione {self.charging_station.name}"
        else:
            context['page_title'] = f"Colonnine del sotto-progetto {self.subproject.name}"
        
        context['project'] = self.subproject.project
        return context

class ChargerDetailView(LoginRequiredMixin, DetailView):
    """Vista per visualizzare una singola colonnina"""
    model = Charger
    template_name = 'projects/charger_detail.html'
    context_object_name = 'charger'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subproject'] = self.object.subproject
        context['project'] = self.object.subproject.project
        context['page_title'] = f"Colonnina {self.object.code}"
        return context

class ChargerCreateView(LoginRequiredMixin, CreateView):
    """Vista per creare una nuova colonnina"""
    model = Charger
    form_class = ChargerForm
    template_name = 'projects/charger_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if 'subproject_id' in self.kwargs:
            kwargs['subproject_id'] = self.kwargs.get('subproject_id')
        if 'charging_station_id' in self.kwargs:
            kwargs['charging_station_id'] = self.kwargs.get('charging_station_id')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if 'subproject_id' in self.kwargs:
            self.subproject = get_object_or_404(CoreSubProject, pk=self.kwargs['subproject_id'])
            self.charging_station = None
            context['subproject'] = self.subproject
            context['project'] = self.subproject.project
            context['page_title'] = f"Aggiungi colonnina a {self.subproject.name}"
        
        elif 'charging_station_id' in self.kwargs:
            from cpo_core.models.charging_station import ChargingStation
            self.charging_station = get_object_or_404(ChargingStation, pk=self.kwargs['charging_station_id'])
            self.subproject = self.charging_station.subproject
            context['charging_station'] = self.charging_station
            context['subproject'] = self.subproject
            context['project'] = self.subproject.project
            context['page_title'] = f"Aggiungi colonnina alla stazione {self.charging_station.name}"
        
        context['form_title'] = "Nuova colonnina"
        return context
    
    def form_valid(self, form):
        if 'subproject_id' in self.kwargs:
            form.instance.subproject_id = self.kwargs.get('subproject_id')
        elif 'charging_station_id' in self.kwargs:
            form.instance.charging_station_id = self.kwargs.get('charging_station_id')
        
        response = super().form_valid(form)
        messages.success(self.request, _("Colonnina aggiunta con successo"))
        return response
    
    def get_success_url(self):
        if 'charging_station_id' in self.kwargs:
            return reverse_lazy('projects:charger_list', kwargs={'charging_station_id': self.kwargs.get('charging_station_id')})
        else:
            return reverse_lazy('projects:charger_list', kwargs={'subproject_id': self.kwargs.get('subproject_id')})

class ChargerUpdateView(LoginRequiredMixin, UpdateView):
    """Vista per modificare una colonnina esistente"""
    model = Charger
    form_class = ChargerForm
    template_name = 'projects/charger_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['subproject_id'] = self.object.subproject_id
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subproject'] = self.object.subproject
        context['project'] = self.object.subproject.project
        context['page_title'] = f"Modifica colonnina {self.object.code}"
        context['form_title'] = f"Modifica colonnina {self.object.code}"
        return context
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Colonnina aggiornata con successo"))
        return response
    
    def get_success_url(self):
        return reverse_lazy('projects:charger_detail', kwargs={'pk': self.object.pk})

class ChargerDeleteView(LoginRequiredMixin, DeleteView):
    """Vista per eliminare una colonnina"""
    model = Charger
    template_name = 'projects/charger_confirm_delete.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subproject'] = self.object.subproject
        context['project'] = self.object.subproject.project
        context['page_title'] = f"Elimina colonnina {self.object.code}"
        return context
    
    def get_success_url(self):
        messages.success(self.request, _("Colonnina eliminata con successo"))
        return reverse_lazy('projects:charger_list', kwargs={'subproject_id': self.object.subproject_id})


# Viste per la gestione delle foto
class ChargingStationPhotoCreateView(LoginRequiredMixin, CreateView):
    """Vista per caricare una nuova foto della stazione di ricarica"""
    model = ChargingStationPhoto
    form_class = ChargingStationPhotoForm
    template_name = 'projects/charging_station_photo_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station_id = self.kwargs.get('station_id')
        
        # Tenta di ottenere una stazione di ricarica
        station = None
        try:
            # Prova prima a ottenere una stazione di ricarica
            station = ChargingStation.objects.filter(pk=station_id).first()
        except:
            pass
            
        # Se non troviamo una stazione, cerchiamo un subproject
        if not station:
            from cpo_core.models.subproject import SubProject
            subproject = get_object_or_404(SubProject, pk=station_id)
            # Qui usiamo subproject_id come charging_station_id
            context['station_id'] = station_id
            context['subproject'] = subproject
            context['project'] = subproject.project
            context['station'] = {"id": station_id, "name": subproject.name}
        else:
            # Se abbiamo trovato una stazione, usiamo quella
            context['station'] = station
            context['subproject'] = station.sub_project
            context['project'] = station.sub_project.project
            
        context['title'] = _('Aggiungi Foto')
        return context
    
    def form_valid(self, form):
        station_id = self.kwargs.get('station_id')
        
        # Tenta di determinare se si tratta di un subproject o di una stazione
        try:
            from cpo_core.models.subproject import SubProject
            # Verifica se esiste un subproject con questo ID
            subproject = SubProject.objects.filter(pk=station_id).first()
            if subproject:
                # È un subproject, usa la relazione subproject
                form.instance.subproject_id = station_id
                form.instance.charging_station_id = None
            else:
                # È una stazione di ricarica, usa la relazione charging_station
                form.instance.charging_station_id = station_id
                form.instance.subproject_id = None
        except Exception as e:
            # In caso di errore, log e prova a usare subproject come fallback
            print(f"Errore nella determinazione del tipo di stazione: {e}")
            form.instance.subproject_id = station_id
            form.instance.charging_station_id = None
        
        # Imposta altri campi comuni
        form.instance.uploaded_by = self.request.user
        if not form.instance.date_taken:
            form.instance.date_taken = timezone.now().date()
            
        messages.success(self.request, _('Foto caricata con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        from cpo_core.models.subproject import SubProject
        station_id = self.kwargs.get('station_id')
        
        # Controlla se si tratta di un subproject
        is_subproject = False
        try:
            subproject = SubProject.objects.get(pk=station_id)
            is_subproject = True
        except:
            pass
            
        if is_subproject:
            return reverse_lazy('projects:subproject_detail', 
                               kwargs={'pk': station_id}) + '#photos'
        else:
            return reverse_lazy('projects:charging_station_detail', 
                               kwargs={'pk': station_id}) + '#photos'


class ChargingStationPhotoUpdateView(LoginRequiredMixin, UpdateView):
    """Vista per modificare una foto della stazione di ricarica"""
    model = ChargingStationPhoto
    form_class = ChargingStationPhotoForm
    template_name = 'projects/charging_station_photo_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Controlla se la foto è associata a un subproject o a una stazione
        if self.object.subproject:
            # La foto è associata a un subproject
            context['subproject'] = self.object.subproject
            context['project'] = self.object.subproject.project
            context['station'] = {"id": self.object.subproject.id, "name": self.object.subproject.name}
        elif self.object.charging_station:
            # La foto è associata a una stazione di ricarica
            context['station'] = self.object.charging_station
            context['subproject'] = self.object.charging_station.sub_project
            context['project'] = self.object.charging_station.sub_project.project
        else:
            # Caso di fallback
            context['station'] = {"id": 0, "name": "Stazione sconosciuta"}
            context['subproject'] = None
            context['project'] = None
        
        context['title'] = _('Modifica Foto')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Foto aggiornata con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        # Determina dove fare redirect in base a cosa è collegato alla foto
        if self.object.subproject:
            return reverse_lazy('projects:subproject_detail', 
                             kwargs={'pk': self.object.subproject.id}) + '#photos'
        elif self.object.charging_station:
            return reverse_lazy('projects:station_detail', 
                             kwargs={'pk': self.object.charging_station.id}) + '#photos'
        else:
            # Redirect generico in caso di problemi
            return reverse_lazy('cpo_core:dashboard')


class ChargingStationPhotoDetailView(LoginRequiredMixin, DetailView):
    """Vista per visualizzare il dettaglio di una foto"""
    model = ChargingStationPhoto
    template_name = 'projects/charging_station_photo_detail.html'
    context_object_name = 'photo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Controlla se la foto è associata a un subproject o a una stazione
        if self.object.subproject:
            # La foto è associata a un subproject
            context['subproject'] = self.object.subproject
            context['project'] = self.object.subproject.project
            context['station'] = {"id": self.object.subproject.id, "name": self.object.subproject.name}
        elif self.object.charging_station:
            # La foto è associata a una stazione di ricarica
            context['station'] = self.object.charging_station
            context['subproject'] = self.object.charging_station.sub_project
            context['project'] = self.object.charging_station.sub_project.project
        else:
            # Caso di fallback
            context['station'] = {"id": 0, "name": "Stazione sconosciuta"}
            context['subproject'] = None
            context['project'] = None
            
        return context


class ChargingStationPhotoDeleteView(LoginRequiredMixin, DeleteView):
    """Vista per eliminare una foto"""
    model = ChargingStationPhoto
    template_name = 'projects/charging_station_photo_confirm_delete.html'
    context_object_name = 'photo'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Controlla se la foto è associata a un subproject o a una stazione
        if self.object.subproject:
            # La foto è associata a un subproject
            context['subproject'] = self.object.subproject
            context['project'] = self.object.subproject.project
            context['station'] = {"id": self.object.subproject.id, "name": self.object.subproject.name}
        elif self.object.charging_station:
            # La foto è associata a una stazione di ricarica
            context['station'] = self.object.charging_station
            context['subproject'] = self.object.charging_station.sub_project
            context['project'] = self.object.charging_station.sub_project.project
        else:
            # Caso di fallback
            context['station'] = {"id": 0, "name": "Stazione sconosciuta"}
            context['subproject'] = None
            context['project'] = None
            
        return context
    
    def form_valid(self, form):
        # Store information about the object before it's deleted
        self.subproject_id = None
        self.charging_station_id = None
        
        if self.object.subproject:
            self.subproject_id = self.object.subproject.id
        if self.object.charging_station:
            self.charging_station_id = self.object.charging_station.id
        
        # Add success message
        messages.success(self.request, _("Foto eliminata con successo"))
        
        # Call parent's form_valid which handles the deletion
        return super().form_valid(form)
        
    def get_success_url(self):
        # Determine where to redirect based on what the photo was linked to
        if hasattr(self, 'subproject_id') and self.subproject_id:
            # Was linked to a subproject
            return reverse_lazy('projects:subproject_detail', 
                            kwargs={'pk': self.subproject_id}) + '#photos'
        elif hasattr(self, 'charging_station_id') and self.charging_station_id:
            # Was linked to a charging station
            return reverse_lazy('projects:station_detail', 
                            kwargs={'pk': self.charging_station_id}) + '#photos'
        else:
            # Fallback
            return reverse_lazy('cpo_core:dashboard')

@require_GET
def usage_profile_detail(request, profile_id):
    """API endpoint per ottenere i dettagli di un profilo di utilizzo"""
    try:
        profile = get_object_or_404(UsageProfile, pk=profile_id)
        
        # Crea un dizionario con i dati del profilo
        profile_data = {
            'id': profile.id,
            'name': profile.name,
            'daily_usage_hours': float(profile.daily_usage_hours),
            'avg_session_kwh': float(profile.avg_session_kwh),
            'utilization_rate': float(profile.utilization_rate),
            'suggested_price_kwh': float(profile.suggested_price_kwh),
            'location_type': profile.location_type,
            # Campi aggiuntivi che potrebbero essere utili
            'description': profile.description,
            'created_at': profile.created_at.isoformat() if hasattr(profile, 'created_at') else None,
            'updated_at': profile.updated_at.isoformat() if hasattr(profile, 'updated_at') else None
        }
        
        return JsonResponse(profile_data)
    except Exception as e:
        return JsonResponse({
            'error': str(e),
            'message': 'Si è verificato un errore nel recupero dei dati del profilo.'
        }, status=500)