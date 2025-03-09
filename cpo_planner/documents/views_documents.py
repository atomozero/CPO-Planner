import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

# Importa tutti i possibili modelli di documenti
from cpo_planner.documents.models import Document, ProjectDocument
try:
    from cpo_planner.projects.models.document import ProjectDocument as ProjectsProjectDocument
except ImportError:
    ProjectsProjectDocument = None


class DocumentDownloadView(LoginRequiredMixin, View):
    """Vista per scaricare un documento, supporta tutti i tipi di documento"""
    
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        document = self.get_document(pk)
        
        if not document:
            messages.error(request, _('Documento non trovato.'))
            return redirect('documents:document_list')
        
        # Controlla l'esistenza del file
        if not document.file:
            messages.error(request, _('Il file non esiste.'))
            return redirect('documents:document_list')
        
        # Scarica il file
        try:
            file_path = document.file.path
            file_name = os.path.basename(document.file.name)
            
            # Usa FileResponse per gestire correttamente il file
            response = FileResponse(
                open(file_path, 'rb'),
                content_type='application/octet-stream',
                as_attachment=True,
                filename=file_name
            )
            return response
        except Exception as e:
            messages.error(request, _('Errore durante il download: {}').format(str(e)))
            return redirect('documents:document_list')
    
    def get_document(self, pk):
        """Trova il documento in qualsiasi modello disponibile"""
        try:
            # Prima prova con Document da documents
            return Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            try:
                # Poi prova con ProjectDocument da documents
                return ProjectDocument.objects.get(pk=pk)
            except ProjectDocument.DoesNotExist:
                if ProjectsProjectDocument:
                    try:
                        # Infine prova con ProjectDocument da projects
                        return ProjectsProjectDocument.objects.get(pk=pk)
                    except ProjectsProjectDocument.DoesNotExist:
                        pass
        return None


class DocumentPreviewView(LoginRequiredMixin, View):
    """Vista per visualizzare l'anteprima di un documento"""
    
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        document = self.get_document(pk)
        
        if not document:
            messages.error(request, _('Documento non trovato.'))
            return redirect('documents:document_list')
        
        # Controlla l'esistenza del file
        if not document.file:
            messages.error(request, _('Il file non esiste.'))
            return redirect('documents:document_list')
        
        # Per i documenti PDF e immagini, restituisci il file per la visualizzazione in-browser
        file_ext = os.path.splitext(document.file.name)[1].lower()
        if file_ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif']:
            try:
                response = FileResponse(
                    open(document.file.path, 'rb'),
                    content_type=self.get_content_type(file_ext)
                )
                return response
            except Exception as e:
                messages.error(request, _('Errore durante l\'anteprima: {}').format(str(e)))
                return redirect('documents:document_list')
        
        # Per altri tipi di file, reindirizza al download
        return redirect('documents:document_download', pk=document.pk)
    
    def get_content_type(self, ext):
        """Determina il content type in base all'estensione del file"""
        if ext == '.pdf':
            return 'application/pdf'
        elif ext in ['.jpg', '.jpeg']:
            return 'image/jpeg'
        elif ext == '.png':
            return 'image/png'
        elif ext == '.gif':
            return 'image/gif'
        else:
            return 'application/octet-stream'
    
    def get_document(self, pk):
        """Trova il documento in qualsiasi modello disponibile"""
        try:
            # Prima prova con Document da documents
            return Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            try:
                # Poi prova con ProjectDocument da documents
                return ProjectDocument.objects.get(pk=pk)
            except ProjectDocument.DoesNotExist:
                if ProjectsProjectDocument:
                    try:
                        # Infine prova con ProjectDocument da projects
                        return ProjectsProjectDocument.objects.get(pk=pk)
                    except ProjectsProjectDocument.DoesNotExist:
                        pass
        return None


class DocumentDeleteView(LoginRequiredMixin, View):
    """Vista per eliminare un documento"""
    
    def get(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        document = self.get_document(pk)
        
        if not document:
            messages.error(request, _('Documento non trovato.'))
            return redirect('documents:document_list')
        
        # Prepara il contesto per la conferma
        return render(request, 'documents/document_confirm_delete.html', {'document': document})
    
    def post(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        document = self.get_document(pk)
        
        if not document:
            messages.error(request, _('Documento non trovato.'))
            return redirect('documents:document_list')
        
        # Elimina il documento
        try:
            document.delete()
            messages.success(request, _('Documento eliminato con successo.'))
            return redirect('documents:document_list')
        except Exception as e:
            messages.error(request, _('Errore durante l\'eliminazione: {}').format(str(e)))
            return redirect('documents:document_list')
    
    def get_document(self, pk):
        """Trova il documento in qualsiasi modello disponibile"""
        try:
            # Prima prova con Document da documents
            return Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            try:
                # Poi prova con ProjectDocument da documents
                return ProjectDocument.objects.get(pk=pk)
            except ProjectDocument.DoesNotExist:
                if ProjectsProjectDocument:
                    try:
                        # Infine prova con ProjectDocument da projects
                        return ProjectsProjectDocument.objects.get(pk=pk)
                    except ProjectsProjectDocument.DoesNotExist:
                        pass
        return None