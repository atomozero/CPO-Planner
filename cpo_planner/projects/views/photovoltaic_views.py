# cpo_planner/projects/views/photovoltaic_views.py
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from ..models.charging_station import ChargingStation
from ..models.photovoltaic import PhotovoltaicSystem
from ..forms.photovoltaic_forms import PhotovoltaicSystemForm

class PhotovoltaicDetailView(LoginRequiredMixin, DetailView):
    model = PhotovoltaicSystem
    template_name = 'projects/photovoltaic_detail.html'
    context_object_name = 'photovoltaic'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.object.charging_station
        context['subproject'] = self.object.charging_station.sub_project
        context['project'] = self.object.charging_station.sub_project.project
        return context

class PhotovoltaicCreateView(LoginRequiredMixin, CreateView):
    model = PhotovoltaicSystem
    form_class = PhotovoltaicSystemForm
    template_name = 'projects/photovoltaic_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station_id = self.kwargs.get('station_id')
        context['station'] = get_object_or_404(ChargingStation, pk=station_id)
        context['subproject'] = context['station'].sub_project
        context['project'] = context['subproject'].project
        context['title'] = _('Aggiungi Impianto Fotovoltaico')
        return context
    
    def form_valid(self, form):
        station_id = self.kwargs.get('station_id')
        station = get_object_or_404(ChargingStation, pk=station_id)
        
        form.instance.charging_station = station
        
        # Imposta il flag sull'oggetto stazione
        station.has_photovoltaic_system = True
        station.photovoltaic_capacity = form.instance.capacity
        station.save()
        
        messages.success(self.request, _('Impianto fotovoltaico aggiunto con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:station_detail', kwargs={'pk': self.kwargs.get('station_id')})

class PhotovoltaicUpdateView(LoginRequiredMixin, UpdateView):
    model = PhotovoltaicSystem
    form_class = PhotovoltaicSystemForm
    template_name = 'projects/photovoltaic_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.object.charging_station
        context['subproject'] = self.object.charging_station.sub_project
        context['project'] = self.object.charging_station.sub_project.project
        context['title'] = _('Modifica Impianto Fotovoltaico')
        return context
    
    def form_valid(self, form):
        # Aggiorna il flag e la capacità sulla stazione
        station = self.object.charging_station
        station.photovoltaic_capacity = form.instance.capacity
        station.save()
        
        messages.success(self.request, _('Impianto fotovoltaico aggiornato con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:photovoltaic_detail', kwargs={'pk': self.object.pk})

class PhotovoltaicDeleteView(LoginRequiredMixin, DeleteView):
    model = PhotovoltaicSystem
    template_name = 'projects/photovoltaic_confirm_delete.html'
    
    def delete(self, request, *args, **kwargs):
        # Rimuovi il flag dalla stazione
        station = self.get_object().charging_station
        station.has_photovoltaic_system = False
        station.photovoltaic_capacity = None
        station.save()
        
        messages.success(request, _('Impianto fotovoltaico eliminato con successo!'))
        return super().delete(request, *args, **kwargs)
    
    def get_success_url(self):
        return reverse_lazy('projects:station_detail', kwargs={'pk': self.object.charging_station.pk})