# cpo_planner/projects/views/charging_station_views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from ..models.subproject import SubProject
from ..models.charging_station import ChargingStation
from ..models.photovoltaic import PhotovoltaicSystem
from ..forms.charging_station_forms import ChargingStationForm, ChargerForm

# Import per le colonnine
from cpo_core.models.subproject import Charger, SubProject as CoreSubProject

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
        form.instance.sub_project_id = self.kwargs.get('subproject_id')
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