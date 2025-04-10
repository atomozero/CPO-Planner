# cpo_planner/projects/views/timeline_views.py
from django.views.generic import DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from projects.models import Project
from ..models.charging_station import ChargingStation
from ..models.timeline import ProjectTimeline, StationTimeline
from ..forms.timeline_forms import ProjectTimelineForm, StationTimelineForm

class ProjectTimelineDetailView(LoginRequiredMixin, DetailView):
    model = ProjectTimeline
    template_name = 'projects/project_timeline_detail.html'
    context_object_name = 'timeline'
    
    def get_object(self, queryset=None):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        return get_object_or_404(ProjectTimeline, project=project)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        
        # Cronoprogramma in formato JSON per il grafico Gantt
        context['timeline_json'] = self.object.export_to_json()
        
        return context

class ProjectTimelineCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectTimeline
    form_class = ProjectTimelineForm
    template_name = 'projects/project_timeline_form.html'
    
    def get_object(self, queryset=None):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        obj, created = ProjectTimeline.objects.get_or_create(project=project)
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        if self.object.pk:
            context['title'] = _('Modifica Cronoprogramma Progetto')
        else:
            context['title'] = _('Crea Cronoprogramma Progetto')
        return context
    
    def form_valid(self, form):
        if form.instance.pk:
            messages.success(self.request, _('Cronoprogramma aggiornato con successo!'))
        else:
            messages.success(self.request, _('Cronoprogramma creato con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:project_timeline_detail', kwargs={
            'project_id': self.kwargs.get('project_id')
        })

class StationTimelineDetailView(LoginRequiredMixin, DetailView):
    model = StationTimeline
    template_name = 'projects/station_timeline_detail.html'
    context_object_name = 'timeline'
    
    def get_object(self, queryset=None):
        station_id = self.kwargs.get('station_id')
        station = get_object_or_404(ChargingStation, pk=station_id)
        return get_object_or_404(StationTimeline, charging_station=station)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = self.object.charging_station
        context['subproject'] = self.object.charging_station.sub_project
        context['project'] = self.object.charging_station.sub_project.project
        
        # Informazioni sul cronoprogramma per visualizzazione
        context['is_delayed'] = self.object.is_delayed()
        context['current_status'] = self.object.get_current_status()
        context['installation_duration'] = self.object.get_installation_duration()
        
        return context

class StationTimelineCreateUpdateView(LoginRequiredMixin, UpdateView):
    model = StationTimeline
    form_class = StationTimelineForm
    template_name = 'projects/station_timeline_form.html'
    
    def get_object(self, queryset=None):
        station_id = self.kwargs.get('station_id')
        station = get_object_or_404(ChargingStation, pk=station_id)
        obj, created = StationTimeline.objects.get_or_create(charging_station=station)
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station_id = self.kwargs.get('station_id')
        context['station'] = get_object_or_404(ChargingStation, pk=station_id)
        context['subproject'] = context['station'].sub_project
        context['project'] = context['subproject'].project
        
        if self.object.pk:
            context['title'] = _('Modifica Cronoprogramma Stazione')
        else:
            context['title'] = _('Crea Cronoprogramma Stazione')
        return context
    
    def form_valid(self, form):
        if form.instance.pk:
            messages.success(self.request, _('Cronoprogramma stazione aggiornato con successo!'))
        else:
            messages.success(self.request, _('Cronoprogramma stazione creato con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:station_timeline_detail', kwargs={
            'project_id': self.kwargs.get('project_id'),
            'station_id': self.kwargs.get('station_id')
        })