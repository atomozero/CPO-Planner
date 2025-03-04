# cpo_planner/projects/views/failure_simulation_views.py
from django.views.generic import DetailView, FormView, View
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from ..models.project import Project
from ..models.failure_simulation import FailureSimulation
from ..forms.failure_simulation_forms import FailureSimulationForm

class FailureSimulationView(LoginRequiredMixin, FormView):
    template_name = 'projects/failure_simulation_form.html'
    form_class = FailureSimulationForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        
        # Ottieni o crea l'oggetto simulazione
        simulation, created = FailureSimulation.objects.get_or_create(project=project)
        
        kwargs['instance'] = simulation
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        context['project'] = get_object_or_404(Project, pk=project_id)
        context['title'] = _('Parametri Simulazione Guasti')
        
        # Se l'oggetto simulazione esiste, mostra i risultati precedenti
        try:
            simulation = FailureSimulation.objects.get(project_id=project_id)
            if simulation.simulation_results:
                context['has_results'] = True
        except FailureSimulation.DoesNotExist:
            context['has_results'] = False
        
        return context
    
    def form_valid(self, form):
        form.save()
        messages.success(self.request, _('Parametri di simulazione salvati con successo!'))
        
        # Reindirizza alla pagina di esecuzione della simulazione
        return redirect('projects:run_failure_simulation', project_id=self.kwargs.get('project_id'))
    
    def get_success_url(self):
        return reverse_lazy('projects:failure_simulation_results', kwargs={
            'project_id': self.kwargs.get('project_id')
        })

class RunFailureSimulationView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        
        # Ottieni l'oggetto simulazione
        try:
            simulation = FailureSimulation.objects.get(project=project)
        except FailureSimulation.DoesNotExist:
            messages.error(request, _('Prima di eseguire la simulazione, configura i parametri!'))
            return redirect('projects:failure_simulation_form', project_id=project_id)
        
        # Esegui la simulazione
        investment_years = project.financial_parameters.investment_years if hasattr(project, 'financial_parameters') else 10
        results = simulation.run_simulation(years=investment_years)
        
        messages.success(request, _('Simulazione guasti eseguita con successo!'))
        return redirect('projects:failure_simulation_results', project_id=project_id)

class FailureSimulationResultsView(LoginRequiredMixin, DetailView):
    model = FailureSimulation
    template_name = 'projects/failure_simulation_results.html'
    context_object_name = 'simulation'
    
    def get_object(self, queryset=None):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        return get_object_or_404(FailureSimulation, project=project)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['results'] = self.object.simulation_results
        return context