# cpo_planner/projects/views/charging_station_views.py
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from ..models.subproject import SubProject
from ..models.charging_station import ChargingStation
from ..models.photovoltaic import PhotovoltaicSystem
from ..forms.charging_station_forms import ChargingStationForm

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