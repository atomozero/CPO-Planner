from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Sum, Count
from django.utils import timezone

from .models import Organization, Project, Municipality, SubProject, ChargingStation, SolarInstallation

def dashboard(request):
    """Dashboard principale dell'applicazione"""
    # Conteggi per la dashboard
    context = {
        'total_projects': Project.objects.count(),
        'active_projects': Project.objects.exclude(status__in=['closed']).count(),
        'total_municipalities': Municipality.objects.count(),
        'total_stations': ChargingStation.objects.count(),
        'operational_stations': ChargingStation.objects.filter(status='operational').count(),
        'projects': Project.objects.order_by('-created_at')[:5],  # Ultimi 5 progetti
        'stations': ChargingStation.objects.order_by('-created_at')[:5],  # Ultime 5 stazioni
    }
    
    # Calcola budget totale e station per stato
    if Project.objects.exists():
        context['total_budget'] = Project.objects.aggregate(Sum('budget'))['budget__sum']
    
    # Dati per grafico stati delle stazioni
    station_status_data = {}
    for status_choice in ChargingStation.STATUS_CHOICES:
        station_status_data[status_choice[1]] = ChargingStation.objects.filter(status=status_choice[0]).count()
    context['station_status_data'] = station_status_data
    
    return render(request, 'core/dashboard.html', context)

# Viste per Organization
class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    context_object_name = 'organizations'
    template_name = 'core/organization_list.html'

class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    context_object_name = 'organization'
    template_name = 'core/organization_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        context['total_budget'] = self.object.projects.aggregate(Sum('budget'))['budget__sum'] or 0
        context['total_projects'] = self.object.projects.count()
        return context

class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    fields = ['name', 'tax_id', 'address', 'contact_email', 'contact_phone']
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Organizzazione creata con successo.')
        return super().form_valid(form)

class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    fields = ['name', 'tax_id', 'address', 'contact_email', 'contact_phone']
    template_name = 'core/organization_form.html'
    
    def get_success_url(self):
        return reverse_lazy('organization_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Organizzazione aggiornata con successo.')
        return super().form_valid(form)

class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'core/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Organizzazione eliminata con successo.')
        return super().delete(request, *args, **kwargs)

# Viste per Project
class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'projects'
    template_name = 'core/project_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtra per stato se specificato nella query
        status_filter = self.request.GET.get('status')
        if status_filter:
            context['projects'] = context['projects'].filter(status=status_filter)
            context['current_status'] = dict(Project.STATUS_CHOICES).get(status_filter)
        
        # Aggiungi statistiche
        context['total_projects'] = context['projects'].count()
        context['total_budget'] = context['projects'].aggregate(Sum('budget'))['budget__sum'] or 0
        
        # Aggiungi scelte di stato per i filtri
        context['status_choices'] = Project.STATUS_CHOICES
        return context

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    context_object_name = 'project'
    template_name = 'core/project_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subprojects'] = self.object.subprojects.all()
        
        # Calcola il totale delle stazioni di ricarica in questo progetto
        subproject_ids = self.object.subprojects.values_list('id', flat=True)
        context['stations_count'] = ChargingStation.objects.filter(subproject_id__in=subproject_ids).count()
        
        # Ottieni le stazioni operative
        context['operational_stations'] = ChargingStation.objects.filter(
            subproject_id__in=subproject_ids, 
            status='operational'
        ).count()
        
        # Statistiche per comuni e stazioni
        context['municipalities_count'] = self.object.subprojects.values('municipality').distinct().count()
        
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ['name', 'description', 'organization', 'project_manager', 'status', 
              'start_date', 'end_date', 'budget', 'loan_amount', 
              'loan_interest_rate', 'loan_term_years', 'pre_amortization_years']
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Progetto creato con successo.')
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ['name', 'description', 'organization', 'project_manager', 'status', 
              'start_date', 'end_date', 'budget', 'loan_amount', 
              'loan_interest_rate', 'loan_term_years', 'pre_amortization_years']
    template_name = 'core/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Progetto aggiornato con successo.')
        return super().form_valid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Progetto eliminato con successo.')
        return super().delete(request, *args, **kwargs)

# Implementa viste simili per Municipality, SubProject, ChargingStation, etc.
# Queste sono le viste di base, le altre seguiranno lo stesso pattern

class MunicipalityListView(LoginRequiredMixin, ListView):
    model = Municipality
    context_object_name = 'municipalities'
    template_name = 'core/municipality_list.html'

class ChargingStationListView(LoginRequiredMixin, ListView):
    model = ChargingStation
    context_object_name = 'stations'
    template_name = 'core/station_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtra per tipo o stato se specificato nella query
        type_filter = self.request.GET.get('type')
        status_filter = self.request.GET.get('status')
        
        if type_filter:
            context['stations'] = context['stations'].filter(station_type=type_filter)
            context['current_type'] = dict(ChargingStation.STATION_TYPES).get(type_filter)
            
        if status_filter:
            context['stations'] = context['stations'].filter(status=status_filter)
            context['current_status'] = dict(ChargingStation.STATUS_CHOICES).get(status_filter)
        
        # Aggiungi statistiche
        context['total_stations'] = context['stations'].count()
        context['operational_stations'] = context['stations'].filter(status='operational').count()
        
        # Aggiungi scelte per i filtri
        context['type_choices'] = ChargingStation.STATION_TYPES
        context['status_choices'] = ChargingStation.STATUS_CHOICES
        return context