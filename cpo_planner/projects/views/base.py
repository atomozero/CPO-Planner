from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.urls import reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from ..models.base import Project, Municipality, ChargingStation

# Viste base per Project

class ProjectListView(ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'


class ProjectCreateView(CreateView):
    model = Project
    template_name = 'projects/project_form.html'
    fields = ['name', 'description', 'start_date', 'end_date']
    success_url = reverse_lazy('projects:project_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Crea nuovo progetto')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Progetto creato con successo!'))
        return super().form_valid(form)


class ProjectUpdateView(UpdateView):
    model = Project
    template_name = 'projects/project_form.html'
    fields = ['name', 'description', 'start_date', 'end_date']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Modifica progetto')
        return context
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Progetto aggiornato con successo!'))
        return super().form_valid(form)


class ProjectDeleteView(DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Progetto eliminato con successo!'))
        return super().form_valid(form)

# Viste per Municipality

class MunicipalityCreateView(CreateView):
    model = Municipality
    template_name = 'projects/municipality_form.html'
    fields = ['name', 'province', 'population']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        context['project'] = get_object_or_404(Project, pk=project_id)
        context['title'] = _('Aggiungi comune')
        return context
    
    def form_valid(self, form):
        form.instance.project_id = self.kwargs.get('project_id')
        messages.success(self.request, _('Comune aggiunto con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.kwargs.get('project_id')})


class MunicipalityUpdateView(UpdateView):
    model = Municipality
    template_name = 'projects/municipality_form.html'
    fields = ['name', 'province', 'population']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['title'] = _('Modifica comune')
        return context
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.project.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Comune aggiornato con successo!'))
        return super().form_valid(form)


class MunicipalityDeleteView(DeleteView):
    model = Municipality
    template_name = 'projects/municipality_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.project.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Comune eliminato con successo!'))
        return super().form_valid(form)

# Viste per ChargingStation

class ChargingStationCreateView(CreateView):
    model = ChargingStation
    template_name = 'projects/charging_station_form.html'
    fields = [
        'name', 'address', 'latitude', 'longitude', 
        'power_type', 'charging_points', 'total_power',
        'station_cost', 'installation_cost', 'connection_cost', 
        'design_cost', 'permit_cost', 'energy_cost_kwh', 
        'charging_price_kwh', 'estimated_sessions_day', 
        'avg_kwh_session', 'installation_date'
    ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        municipality_id = self.kwargs.get('municipality_id')
        context['municipality'] = get_object_or_404(Municipality, pk=municipality_id)
        context['project'] = context['municipality'].project
        context['title'] = _('Aggiungi stazione di ricarica')
        return context
    
    def form_valid(self, form):
        form.instance.municipality_id = self.kwargs.get('municipality_id')
        messages.success(self.request, _('Stazione di ricarica aggiunta con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        municipality = get_object_or_404(Municipality, pk=self.kwargs.get('municipality_id'))
        return reverse_lazy('projects:project_detail', kwargs={'pk': municipality.project.pk})


class ChargingStationDetailView(DetailView):
    model = ChargingStation
    template_name = 'projects/charging_station_detail.html'
    context_object_name = 'station'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.municipality.project
        return context


class ChargingStationUpdateView(UpdateView):
    model = ChargingStation
    template_name = 'projects/charging_station_form.html'
    fields = [
        'name', 'address', 'latitude', 'longitude', 
        'power_type', 'charging_points', 'total_power',
        'station_cost', 'installation_cost', 'connection_cost', 
        'design_cost', 'permit_cost', 'energy_cost_kwh', 
        'charging_price_kwh', 'estimated_sessions_day', 
        'avg_kwh_session', 'installation_date'
    ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['municipality'] = self.object.municipality
        context['project'] = self.object.municipality.project
        context['title'] = _('Modifica stazione di ricarica')
        return context
    
    def get_success_url(self):
        return reverse_lazy('projects:station_detail', 
                           kwargs={
                               'pk': self.object.pk,
                               'project_id': self.object.municipality.project.pk
                           })
    
    def form_valid(self, form):
        messages.success(self.request, _('Stazione di ricarica aggiornata con successo!'))
        return super().form_valid(form)


class ChargingStationDeleteView(DeleteView):
    model = ChargingStation
    template_name = 'projects/charging_station_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', 
                           kwargs={'pk': self.object.municipality.project.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Stazione di ricarica eliminata con successo!'))
        return super().form_valid(form)