# cpo_planner/projects/views/project_views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.shortcuts import redirect
from django.db import transaction

# Importa dai modelli consolidati
from cpo_core.models.project import Project
from cpo_core.models.subproject import SubProject
from ..forms.project_forms import ProjectForm

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    ordering = ['-start_date']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        # Ensure budget calculations are up to date
        for project in queryset:
            project.calculate_total_metrics()
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Progetti')
        return context

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Aggiunge sotto-progetti
        context['subprojects'] = SubProject.objects.filter(project=self.object)
        
        # Statistiche finanziarie
        if hasattr(self.object, 'financial_analysis'):
            context['financial_analysis'] = self.object.financial_analysis
        
        # Cronoprogramma
        if hasattr(self.object, 'timeline'):
            context['timeline'] = self.object.timeline
        
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    success_url = reverse_lazy('projects:project_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Crea Nuovo Progetto')
        return context
    
    def form_valid(self, form):
        self.object = form.save()
        messages.success(self.request, _('Progetto creato con successo!'))
        return super(CreateView, self).form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Modifica Progetto')
        return context
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, _('Progetto aggiornato con successo!'))
        return super().form_valid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('projects:project_list')
    
    def form_valid(self, form):
        try:
            self.object = self.get_object()
            
            # Ottieni l'ID prima di eliminare
            project_id = self.object.id
            project_name = self.object.name
            
            # Bypassa il sistema di eliminazione in cascata di Django
            # ed esegui direttamente la query SQL
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM projects_project WHERE id = %s", [project_id])
            
            messages.success(self.request, _(f'Progetto "{project_name}" eliminato con successo!'))
            return redirect('projects:project_list')
        except Exception as e:
            messages.error(self.request, _('Errore durante l\'eliminazione: {}').format(str(e)))
            return redirect('projects:project_list')
            
    def delete(self, request, *args, **kwargs):
        # Questo metodo è deprecato ma lo manteniamo per compatibilità
        return self.form_valid(None)