# documents/views.py
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.conf import settings

from cpo_planner.projects.models import Project, SubProject, ChargingStation
from .models import (
    Document, DocumentCategory, DocumentNote, DocumentTask,
    DocumentStatus, DocumentTaskStatus
)
from .forms import (
    DocumentForm, DocumentNoteForm, DocumentTaskForm,
    DocumentFilterForm, DocumentCategoryForm
)

class DocumentListView(LoginRequiredMixin, ListView):
    """Vista per elencare i documenti con opzioni di filtro"""
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Ottiene l'entità collegata se specificata
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            if entity_type == 'project':
                content_type = ContentType.objects.get_for_model(Project)
                entity = get_object_or_404(Project, id=entity_id)
            elif entity_type == 'subproject':
                content_type = ContentType.objects.get_for_model(SubProject)
                entity = get_object_or_404(SubProject, id=entity_id)
            elif entity_type == 'chargingstation':
                content_type = ContentType.objects.get_for_model(ChargingStation)
                entity = get_object_or_404(ChargingStation, id=entity_id)
            else:
                raise Http404(_("Tipo di entità non valido"))
                
            queryset = queryset.filter(content_type=content_type, object_id=entity_id)
            self.entity = entity
        
        # Applica i filtri dal form
        form = DocumentFilterForm(self.request.GET)
        if form.is_valid():
            # Filtro per categoria
            category = form.cleaned_data.get('category')
            if category:
                queryset = queryset.filter(category=category)
            
            # Filtro per stato
            status = form.cleaned_data.get('status')
            if status:
                queryset = queryset.filter(status=status)
            
            # Ricerca testuale
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(title__icontains=search) | 
                    Q(description__icontains=search)
                )
            
            # Filtri per data
            date_from = form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__gte=date_from)
                
            date_to = form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset.select_related('category', 'created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = DocumentFilterForm(self.request.GET)
        
        # Aggiunge informazioni sull'entità se specificata
        if hasattr(self, 'entity'):
            context['entity'] = self.entity
            context['entity_type'] = self.kwargs.get('entity_type')
        
        # Aggiunge statistiche sui documenti
        context['total_documents'] = self.get_queryset().count()
        context['pending_documents'] = self.get_queryset().filter(status=DocumentStatus.PENDING).count()
        context['expired_documents'] = self.get_queryset().filter(status=DocumentStatus.EXPIRED).count()
        
        return context

class DocumentDetailView(LoginRequiredMixin, DetailView):
    """Vista dettaglio di un documento"""
    model = Document
    template_name = 'documents/document_detail.html'
    context_object_name = 'document'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ottiene l'entità collegata al documento
        document = self.get_object()
        content_type = document.content_type
        object_id = document.object_id
        
        if content_type.model == 'project':
            context['entity'] = Project.objects.get(id=object_id)
            context['entity_type'] = 'project'
        elif content_type.model == 'subproject':
            context['entity'] = SubProject.objects.get(id=object_id)
            context['entity_type'] = 'subproject'
        elif content_type.model == 'chargingstation':
            context['entity'] = ChargingStation.objects.get(id=object_id)
            context['entity_type'] = 'chargingstation'
        
        # Form per aggiungere note
        context['note_form'] = DocumentNoteForm()
        
        # Form per aggiungere attività
        context['task_form'] = DocumentTaskForm()
        
        # Note e attività esistenti
        context['notes'] = document.notes.select_related('created_by').order_by('-created_at')
        context['tasks'] = document.tasks.select_related('assigned_to', 'created_by').order_by('-due_date')
        
        return context

class DocumentCreateView(LoginRequiredMixin, CreateView):
    """Vista per creare un nuovo documento"""
    model = Document
    form_class = DocumentForm
    template_name = 'documents/document_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Se il documento è collegato a un'entità specifica
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            if entity_type == 'project':
                entity_obj = get_object_or_404(Project, id=entity_id)
            elif entity_type == 'subproject':
                entity_obj = get_object_or_404(SubProject, id=entity_id)
            elif entity_type == 'chargingstation':
                entity_obj = get_object_or_404(ChargingStation, id=entity_id)
            else:
                raise Http404(_("Tipo di entità non valido"))
                
            kwargs['entity_obj'] = entity_obj
            kwargs['entity_type'] = entity_type
            
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aggiunge informazioni sull'entità se specificata
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            if entity_type == 'project':
                context['entity'] = get_object_or_404(Project, id=entity_id)
            elif entity_type == 'subproject':
                context['entity'] = get_object_or_404(SubProject, id=entity_id)
            elif entity_type == 'chargingstation':
                context['entity'] = get_object_or_404(ChargingStation, id=entity_id)
                
            context['entity_type'] = entity_type
            
        return context
    
    def get_success_url(self):
        messages.success(self.request, _('Documento creato con successo.'))
        
        # Reindirizza alla lista documenti per l'entità specificata
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            return reverse('documents:document_list_entity', kwargs={
                'entity_type': entity_type,
                'entity_id': entity_id
            })
            
        return reverse('documents:document_detail', kwargs={'pk': self.object.pk})

class DocumentUpdateView(LoginRequiredMixin, UpdateView):
    """Vista per modificare un documento esistente"""
    model = Document
    form_class = DocumentForm
    template_name = 'documents/document_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context
    
    def get_success_url(self):
        messages.success(self.request, _('Documento aggiornato con successo.'))
        return reverse('documents:document_detail', kwargs={'pk': self.object.pk})

class DocumentDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista per eliminare un documento"""
    model = Document
    template_name = 'documents/document_confirm_delete.html'
    permission_required = 'documents.delete_document'
    
    def get_success_url(self):
        messages.success(self.request, _('Documento eliminato con successo.'))
        
        # Prova a ottenere l'entità collegata
        document = self.get_object()
        content_type = document.content_type
        object_id = document.object_id
        
        if content_type.model == 'project':
            return reverse('documents:document_list_entity', kwargs={
                'entity_type': 'project',
                'entity_id': object_id
            })
        elif content_type.model == 'subproject':
            return reverse('documents:document_list_entity', kwargs={
                'entity_type': 'subproject',
                'entity_id': object_id
            })
        elif content_type.model == 'chargingstation':
            return reverse('documents:document_list_entity', kwargs={
                'entity_type': 'chargingstation',
                'entity_id': object_id
            })
            
        return reverse('documents:document_list')

class AddDocumentNoteView(LoginRequiredMixin, FormView):
    """Vista per aggiungere una nota a un documento"""
    form_class = DocumentNoteForm
    http_method_names = ['post']
    
    def form_valid(self, form):
        document = get_object_or_404(Document, pk=self.kwargs.get('pk'))
        
        # Crea la nota
        note = form.save(commit=False)
        note.document = document
        note.created_by = self.request.user
        note.save()
        
        messages.success(self.request, _('Nota aggiunta con successo.'))
        return redirect('documents:document_detail', pk=document.pk)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Errore nell\'aggiunta della nota.'))
        return redirect('documents:document_detail', pk=self.kwargs.get('pk'))

class AddDocumentTaskView(LoginRequiredMixin, FormView):
    """Vista per aggiungere un'attività a un documento"""
    form_class = DocumentTaskForm
    http_method_names = ['post']
    
    def form_valid(self, form):
        document = get_object_or_404(Document, pk=self.kwargs.get('pk'))
        
        # Crea l'attività
        task = form.save(commit=False)
        task.document = document
        task.created_by = self.request.user
        task.save()
        
        messages.success(self.request, _('Attività aggiunta con successo.'))
        return redirect('documents:document_detail', pk=document.pk)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Errore nell\'aggiunta dell\'attività.'))
        return redirect('documents:document_detail', pk=self.kwargs.get('pk'))

class UpdateDocumentTaskView(LoginRequiredMixin, UpdateView):
    """Vista per aggiornare lo stato di un'attività"""
    model = DocumentTask
    fields = ['status']
    http_method_names = ['post']
    
    def form_valid(self, form):
        task = self.get_object()
        
        # Aggiorna lo stato
        task = form.save(commit=False)
        
        # Se stiamo completando l'attività, imposta la data di completamento
        if task.status == DocumentTaskStatus.COMPLETED and not task.completed_at:
            task.completed_at = timezone.now()
            
        task.save()
        
        messages.success(self.request, _('Stato dell\'attività aggiornato.'))
        return redirect('documents:document_detail', pk=task.document.pk)

class DocumentCategoryListView(LoginRequiredMixin, ListView):
    """Vista per elencare le categorie di documenti"""
    model = DocumentCategory
    template_name = 'documents/document_category_list.html'
    context_object_name = 'categories'

class DocumentCategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista per creare una nuova categoria di documenti"""
    model = DocumentCategory
    form_class = DocumentCategoryForm
    template_name = 'documents/document_category_form.html'
    permission_required = 'documents.add_documentcategory'
    success_url = reverse_lazy('documents:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Categoria creata con successo.'))
        return super().form_valid(form)

class DocumentCategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista per aggiornare una categoria di documenti"""
    model = DocumentCategory
    form_class = DocumentCategoryForm
    template_name = 'documents/document_category_form.html'
    permission_required = 'documents.change_documentcategory'
    success_url = reverse_lazy('documents:category_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Categoria aggiornata con successo.'))
        return super().form_valid(form)

class DocumentCategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista per eliminare una categoria di documenti"""
    model = DocumentCategory
    template_name = 'documents/document_category_confirm_delete.html'
    permission_required = 'documents.delete_documentcategory'
    success_url = reverse_lazy('documents:category_list')
    
    def form_valid(self, form):
        try:
            response = super().form_valid(form)
            messages.success(self.request, _('Categoria eliminata con successo.'))
            return response
        except models.ProtectedError:
            messages.error(self.request, _('Impossibile eliminare la categoria perché è in uso.'))
            return redirect('documents:category_list')

class DocumentDownloadView(LoginRequiredMixin, DetailView):
    """Vista per scaricare un documento"""
    model = Document
    
    def get(self, request, *args, **kwargs):
        document = self.get_object()
        if not document.file:
            messages.error(request, _('Il file non esiste.'))
            return redirect('documents:document_detail', pk=document.pk)
            
        # Costruisci il percorso del file
        file_path = document.file.path
        
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename={os.path.basename(file_path)}'
                return response
                
        messages.error(request, _('Il file non esiste.'))
        return redirect('documents:document_detail', pk=document.pk)

class DocumentPreviewView(LoginRequiredMixin, DetailView):
    """Vista per visualizzare l'anteprima di un documento"""
    model = Document
    template_name = 'documents/document_preview.html'
    context_object_name = 'document'

def update_document_status(request, pk):
    """Aggiorna lo stato di un documento tramite AJAX"""
    if not request.is_ajax() or request.method != 'POST':
        raise PermissionDenied
        
    document = get_object_or_404(Document, pk=pk)
    new_status = request.POST.get('status')
    
    if new_status in [s[0] for s in DocumentStatus.choices]:
        document.status = new_status
        document.save()
        return JsonResponse({'status': 'success'})
        
    return JsonResponse({'status': 'error', 'message': _('Stato non valido')}, status=400)