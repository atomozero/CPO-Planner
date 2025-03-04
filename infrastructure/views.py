# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages

from .models import Municipality, ChargingProject, ChargingStation
from .forms import MunicipalityForm, ChargingProjectForm, ChargingStationForm

from .models import ProjectTask
from .forms import ProjectTaskForm

from django.http import HttpResponse
from .reports import MunicipalityReportGenerator, ChargingProjectReportGenerator, ChargingStationSheetGenerator


# Viste per i Comuni
class MunicipalityListView(LoginRequiredMixin, ListView):
    model = Municipality
    context_object_name = 'municipalities'
    template_name = 'municipalities/municipality_list.html'
    
class MunicipalityDetailView(LoginRequiredMixin, DetailView):
    model = Municipality
    context_object_name = 'municipality'
    template_name = 'municipalities/municipality_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.charging_projects.all()
        return context

class MunicipalityCreateView(LoginRequiredMixin, CreateView):
    model = Municipality
    form_class = MunicipalityForm
    template_name = 'municipalities/municipality_form.html'
    success_url = reverse_lazy('municipality-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Comune {form.instance.name} creato con successo!")
        return super().form_valid(form)

# Viste per i Progetti
class ChargingProjectListView(LoginRequiredMixin, ListView):
    model = ChargingProject
    context_object_name = 'projects'
    template_name = 'projects/project_list.html'
    
class ChargingProjectDetailView(LoginRequiredMixin, DetailView):
    model = ChargingProject
    context_object_name = 'project'
    template_name = 'projects/project_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stations'] = self.object.charging_stations.all()
        return context

class ChargingProjectCreateView(LoginRequiredMixin, CreateView):
    model = ChargingProject
    form_class = ChargingProjectForm
    template_name = 'projects/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f"Progetto {form.instance.name} creato con successo!")
        return super().form_valid(form)

# Viste per le Stazioni di Ricarica
class ChargingStationListView(LoginRequiredMixin, ListView):
    model = ChargingStation
    context_object_name = 'stations'
    template_name = 'stations/station_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Sum, Count, Case, When, IntegerField
        
        # Statistiche di base
        context['active_stations'] = ChargingStation.objects.filter(status='active').count()
        context['total_power'] = ChargingStation.objects.aggregate(Sum('power_kw'))['power_kw__sum'] or 0
        context['total_projects'] = ChargingProject.objects.filter(charging_stations__isnull=False).distinct().count()
        
        # Stazioni con coordinate per la mappa
        context['stations_with_coords'] = ChargingStation.objects.filter(latitude__isnull=False, longitude__isnull=False)
        
        # Conteggi per stato
        context['status_counts'] = {
            'planned': ChargingStation.objects.filter(status='planned').count(),
            'installing': ChargingStation.objects.filter(status='installing').count(),
            'active': ChargingStation.objects.filter(status='active').count(),
            'maintenance': ChargingStation.objects.filter(status='maintenance').count(),
            'inactive': ChargingStation.objects.filter(status='inactive').count(),
        }
        
        # Distribuzione potenza
        context['power_distribution'] = [
            {'range': '0-22 kW', 'count': ChargingStation.objects.filter(power_kw__lte=22).count()},
            {'range': '23-50 kW', 'count': ChargingStation.objects.filter(power_kw__gt=22, power_kw__lte=50).count()},
            {'range': '51-100 kW', 'count': ChargingStation.objects.filter(power_kw__gt=50, power_kw__lte=100).count()},
            {'range': '101-150 kW', 'count': ChargingStation.objects.filter(power_kw__gt=100, power_kw__lte=150).count()},
            {'range': '151+ kW', 'count': ChargingStation.objects.filter(power_kw__gt=150).count()},
        ]
        
        return context
    
class ChargingStationDetailView(LoginRequiredMixin, DetailView):
    model = ChargingStation
    context_object_name = 'station'
    template_name = 'stations/station_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Puoi aggiungere qui dati simulati per le statistiche
        # Esempio:
        context['usage_percentage'] = 25  # percentuale di tempo in uso
        context['ready_percentage'] = 70  # percentuale di tempo pronta
        context['unavailable_percentage'] = 5  # percentuale di tempo non disponibile
        
        # Dati ricavi mensili (simulati)
        context['monthly_revenue'] = {
            'jan': 120, 'feb': 140, 'mar': 160, 'apr': 190,
            'may': 210, 'jun': 240, 'jul': 260, 'aug': 280,
            'sep': 250, 'oct': 220, 'nov': 180, 'dec': 150
        }
        
        return context
class ChargingStationCreateView(LoginRequiredMixin, CreateView):
    model = ChargingStation
    form_class = ChargingStationForm
    template_name = 'stations/station_form.html'
    
    def get_success_url(self):
        return reverse_lazy('station-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Se il progetto è fornito nell'URL, assegniamolo alla stazione
        project_id = self.kwargs.get('project_id')
        if project_id:
            form.instance.project_id = project_id
        
        messages.success(self.request, f"Stazione di ricarica {form.instance.code} creata con successo!")
        return super().form_valid(form)



class ProjectTaskListView(LoginRequiredMixin, ListView):
    model = ProjectTask
    context_object_name = 'tasks'
    template_name = 'tasks/task_list.html'
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        if project_id:
            return ProjectTask.objects.filter(project_id=project_id)
        return ProjectTask.objects.all()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        if project_id:
            context['project'] = get_object_or_404(ChargingProject, pk=project_id)
        return context

class ProjectTaskCreateView(LoginRequiredMixin, CreateView):
    model = ProjectTask
    form_class = ProjectTaskForm
    template_name = 'tasks/task_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        project_id = self.kwargs.get('project_id')
        if project_id:
            form.fields['project'].initial = project_id
            # Filtra le dipendenze solo per il progetto corrente
            form.fields['dependencies'].queryset = ProjectTask.objects.filter(project_id=project_id)
        return form
    
    def get_success_url(self):
        project_id = self.kwargs.get('project_id') or self.object.project.id
        return reverse_lazy('project-tasks', kwargs={'project_id': project_id})
    
    def form_valid(self, form):
        project_id = self.kwargs.get('project_id')
        if project_id:
            form.instance.project_id = project_id
        
        messages.success(self.request, f"Attività '{form.instance.name}' creata con successo!")
        return super().form_valid(form)

class ProjectTaskUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectTask
    form_class = ProjectTaskForm
    template_name = 'tasks/task_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtra le dipendenze solo per il progetto corrente, escludendo se stessa
        form.fields['dependencies'].queryset = ProjectTask.objects.filter(
            project=self.object.project
        ).exclude(pk=self.object.pk)
        return form
    
    def get_success_url(self):
        return reverse_lazy('project-tasks', kwargs={'project_id': self.object.project.id})
    
    def form_valid(self, form):
        messages.success(self.request, f"Attività '{form.instance.name}' aggiornata con successo!")
        return super().form_valid(form)
    

def project_gantt_view(request, project_id):
    project = get_object_or_404(ChargingProject, pk=project_id)
    tasks = project.tasks.all()
    
    # Prepara il contesto
    context = {
        'project': project,
        'tasks': tasks,
    }
    
    return render(request, 'projects/project_gantt.html', context)

def generate_municipality_report(request, pk):
    municipality = get_object_or_404(Municipality, pk=pk)
    
    # Genera il PDF
    buffer = BytesIO()
    report_generator = MunicipalityReportGenerator(municipality, buffer)
    pdf = report_generator.generate()
    
    # Crea la risposta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{municipality.name}_report.pdf"'
    response.write(pdf.getvalue())
    
    return response

def generate_project_report(request, pk):
    project = get_object_or_404(ChargingProject, pk=pk)
    
    # Genera il PDF
    buffer = BytesIO()
    report_generator = ChargingProjectReportGenerator(project, buffer)
    pdf = report_generator.generate()
    
    # Crea la risposta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{project.name}_business_plan.pdf"'
    response.write(pdf.getvalue())
    
    return response

def generate_station_sheet(request, pk):
    station = get_object_or_404(ChargingStation, pk=pk)
    
    # Genera il PDF
    buffer = BytesIO()
    sheet_generator = ChargingStationSheetGenerator(station, buffer)
    pdf = sheet_generator.generate()
    
    # Crea la risposta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{station.code}_scheda_tecnica.pdf"'
    response.write(pdf.getvalue())
    
    return response