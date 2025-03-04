# cpo_planner/projects/views/subproject_views.py
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

from ..models.project import Project
from ..models.subproject import SubProject
from ..models.municipality import Municipality
from ..forms.subproject_forms import SubProjectForm

class SubProjectDetailView(LoginRequiredMixin, DetailView):
    model = SubProject
    template_name = 'projects/subproject_detail.html'
    context_object_name = 'subproject'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['stations'] = self.object.chargingstation_set.all()
        return context

class SubProjectCreateView(LoginRequiredMixin, CreateView):
    model = SubProject
    form_class = SubProjectForm
    template_name = 'projects/subproject_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_id'] = self.kwargs.get('project_id')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        context['project'] = get_object_or_404(Project, pk=project_id)
        context['title'] = _('Crea Nuovo Sotto-Progetto')
        return context
    
    def form_valid(self, form):
        form.instance.project_id = self.kwargs.get('project_id')
        messages.success(self.request, _('Sotto-progetto creato con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.kwargs.get('project_id')})

class SubProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = SubProject
    form_class = SubProjectForm
    template_name = 'projects/subproject_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_id'] = self.object.project_id
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['title'] = _('Modifica Sotto-Progetto')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Sotto-progetto aggiornato con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:subproject_detail', kwargs={'pk': self.object.pk})

class SubProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = SubProject
    template_name = 'projects/subproject_confirm_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.project.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Sotto-progetto eliminato con successo!'))
        return super().delete(request, *args, **kwargs)