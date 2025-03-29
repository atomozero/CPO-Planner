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
        try:
            # Estrai il municipality dal form
            municipality = form.cleaned_data.get('municipality')
            
            # Debug info
            print(f"DEBUG: ProjectCreateView - municipality selezionato: {municipality} (ID: {municipality.id if hasattr(municipality, 'id') else 'None'})")
            
            # Rimuovi il campo municipality dal form
            municipality_id = None
            if municipality:
                if hasattr(municipality, 'id'):
                    municipality_id = municipality.id
                elif isinstance(municipality, int) or (isinstance(municipality, str) and municipality.isdigit()):
                    municipality_id = int(municipality)
                
                # Rimuovi municipality per evitare problemi
                form.cleaned_data.pop('municipality', None)
            
            # Salva il progetto senza municipality
            self.object = form.save(commit=False)
            
            # Imposta direttamente municipality_id
            if municipality_id:
                print(f"DEBUG: Impostazione diretta municipality_id={municipality_id}")
                self.object.municipality_id = municipality_id
            
            # Salva l'oggetto
            self.object.save()
            
            # Salva i campi ManyToMany
            form.save_m2m()
            
            # Debug dopo il salvataggio
            print(f"DEBUG: Dopo salvataggio - municipality_id: {self.object.municipality_id}")
            
            # Se il municipio è stato impostato, forza la sincronizzazione
            if self.object.municipality_id:
                print(f"DEBUG: Forzatura sincronizzazione municipality per nuovo progetto {self.object.id}")
                self.object.refresh_from_db()
                self.object.sync_municipalities()
            
            messages.success(self.request, _('Progetto creato con successo!'))
            return redirect(self.get_success_url())
            
        except Exception as e:
            import traceback
            print(f"ERRORE nel salvataggio: {str(e)}")
            print(traceback.format_exc())
            messages.error(self.request, f"Errore durante il salvataggio: {str(e)}")
            return self.form_invalid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Debug: stampa il valore di municipality prima del salvataggio
        municipality = form.cleaned_data.get('municipality')
        print(f"DEBUG: ProjectUpdateView - municipality selezionato: {municipality} (ID: {municipality.id if municipality else 'None'})")
        
        # Controlla se il municipio è cambiato rispetto al valore salvato nel database
        has_changed = False
        if self.object.pk:
            original_municipality_id = Project.objects.filter(pk=self.object.pk).values_list('municipality_id', flat=True).first()
            new_municipality_id = municipality.id if municipality else None
            has_changed = original_municipality_id != new_municipality_id
            print(f"DEBUG: Municipality changed? {has_changed} (Original: {original_municipality_id}, New: {new_municipality_id})")
        
        # Salva l'oggetto normalmente
        with transaction.atomic():
            self.object = form.save()
            
            # Se il municipio è cambiato, forza la sincronizzazione manualmente
            if has_changed and municipality:
                print(f"DEBUG: Forzatura sincronizzazione municipality per progetto {self.object.id}")
                self.object.sync_municipalities()
        
        # Verifica che il municipio sia stato aggiornato correttamente
        self.object.refresh_from_db()
        print(f"DEBUG: Dopo salvataggio - municipality: {self.object.municipality} (ID: {self.object.municipality_id if self.object.municipality else 'None'})")
        
        # Verifica subproject
        from cpo_core.models.subproject import SubProject
        subprojects = SubProject.objects.filter(project=self.object)
        for sp in subprojects:
            print(f"DEBUG: Subproject {sp.id} ({sp.name}) - municipality: {sp.municipality} (ID: {sp.municipality_id})")
        
        messages.success(self.request, _('Progetto aggiornato con successo!'))
        return super(UpdateView, self).form_valid(form)

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
            
            # Elimina prima tutti i sottoprogetti associati
            from cpo_core.models.subproject import SubProject
            from cpo_core.models.charging_station import ChargingStation, ChargingStationPhoto
            from django.db import transaction
            
            with transaction.atomic():
                # Trova tutti i sottoprogetti associati
                subprojects = SubProject.objects.filter(project_id=project_id)
                
                # Per ogni sottoprogetto, elimina tutte le stazioni di ricarica e le foto associate
                for subproject in subprojects:
                    # Elimina le foto delle stazioni di ricarica associate
                    ChargingStationPhoto.objects.filter(subproject=subproject).delete()
                    
                    # Elimina le stazioni di ricarica associate
                    ChargingStation.objects.filter(subproject=subproject).delete()
                
                # Elimina tutti i sottoprogetti
                subprojects.delete()
                
                # Infine, elimina il progetto principale
                self.object.delete()
            
            messages.success(self.request, _(f'Progetto "{project_name}" eliminato con successo!'))
            return redirect('projects:project_list')
        except Exception as e:
            messages.error(self.request, _('Errore durante l\'eliminazione: {}').format(str(e)))
            return redirect('projects:project_list')