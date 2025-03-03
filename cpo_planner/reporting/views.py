# reporting/views.py
import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.paginator import Paginator

from cpo_planner.projects.models import Project, SubProject, ChargingStation
from .models import (
    ReportTemplate, TemplatePlaceholder, Report, 
    ReportPlaceholderValue, ReportType
)
from .forms import (
    ReportTemplateForm, TemplatePlaceholderForm,
    TemplatePlaceholderFormSet, ReportForm,
    PlaceholderValueForm, ReportFilterForm
)
from .services import generate_report_async, generate_bulk_reports
from .tasks import generate_report_task

class ReportTemplateListView(LoginRequiredMixin, ListView):
    """Vista per elencare i template di report"""
    model = ReportTemplate
    template_name = 'reporting/template_list.html'
    context_object_name = 'templates'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtra per tipo
        report_type = self.request.GET.get('type')
        if report_type:
            queryset = queryset.filter(type=report_type)
            
        # Filtra per ricerca testuale
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_types'] = ReportType.choices
        return context

class ReportTemplateDetailView(LoginRequiredMixin, DetailView):
    """Vista per visualizzare i dettagli di un template"""
    model = ReportTemplate
    template_name = 'reporting/template_detail.html'
    context_object_name = 'template'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['placeholders'] = self.object.placeholders.all()
        return context

class ReportTemplateCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista per creare un nuovo template di report"""
    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = 'reporting/template_form.html'
    permission_required = 'reporting.add_reporttemplate'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['placeholder_formset'] = TemplatePlaceholderFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['placeholder_formset'] = TemplatePlaceholderFormSet(instance=self.object)
            
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        placeholder_formset = context['placeholder_formset']
        
        if placeholder_formset.is_valid():
            self.object = form.save()
            placeholder_formset.instance = self.object
            placeholder_formset.save()
            messages.success(self.request, _('Template creato con successo.'))
            return redirect('reporting:template_detail', pk=self.object.pk)
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('reporting:template_detail', kwargs={'pk': self.object.pk})

class ReportTemplateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista per aggiornare un template esistente"""
    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = 'reporting/template_form.html'
    permission_required = 'reporting.change_reporttemplate'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        if self.request.POST:
            context['placeholder_formset'] = TemplatePlaceholderFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['placeholder_formset'] = TemplatePlaceholderFormSet(instance=self.object)
            
        context['is_update'] = True
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        placeholder_formset = context['placeholder_formset']
        
        if placeholder_formset.is_valid():
            self.object = form.save()
            placeholder_formset.instance = self.object
            placeholder_formset.save()
            messages.success(self.request, _('Template aggiornato con successo.'))
            return redirect('reporting:template_detail', pk=self.object.pk)
        else:
            return self.form_invalid(form)
    
    def get_success_url(self):
        return reverse('reporting:template_detail', kwargs={'pk': self.object.pk})

class ReportTemplateDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista per eliminare un template"""
    model = ReportTemplate
    template_name = 'reporting/template_confirm_delete.html'
    permission_required = 'reporting.delete_reporttemplate'
    success_url = reverse_lazy('reporting:template_list')
    
    def delete(self, request, *args, **kwargs):
        try:
            result = super().delete(request, *args, **kwargs)
            messages.success(request, _('Template eliminato con successo.'))
            return result
        except ProtectedError:
            messages.error(request, _('Impossibile eliminare il template perché è in uso.'))
            return redirect('reporting:template_list')

class ReportListView(LoginRequiredMixin, ListView):
    """Vista per elencare i report"""
    model = Report
    template_name = 'reporting/report_list.html'
    context_object_name = 'reports'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        form = ReportFilterForm(self.request.GET)
        
        if form.is_valid():
            # Filtra per tipo di report
            report_type = form.cleaned_data.get('report_type')
            if report_type:
                queryset = queryset.filter(template__type=report_type)
            
            # Filtra per entità
            entity_type = form.cleaned_data.get('entity_type')
            if entity_type:
                if entity_type == 'project':
                    content_type = ContentType.objects.get_for_model(Project)
                    queryset = queryset.filter(content_type=content_type)
                elif entity_type == 'subproject':
                    content_type = ContentType.objects.get_for_model(SubProject)
                    queryset = queryset.filter(content_type=content_type)
                elif entity_type == 'chargingstation':
                    content_type = ContentType.objects.get_for_model(ChargingStation)
                    queryset = queryset.filter(content_type=content_type)
                elif entity_type == 'none':
                    queryset = queryset.filter(content_type__isnull=True)
            
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
        
        return queryset.select_related('template', 'created_by')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ReportFilterForm(self.request.GET)
        return context

class ReportDetailView(LoginRequiredMixin, DetailView):
    """Vista per visualizzare i dettagli di un report"""
    model = Report
    template_name = 'reporting/report_detail.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()
        
        # Ottieni l'entità collegata
        if report.content_type and report.object_id:
            content_type = report.content_type
            object_id = report.object_id
            
            if content_type.model == 'project':
                context['entity'] = Project.objects.get(id=object_id)
                context['entity_type'] = 'project'
            elif content_type.model == 'subproject':
                context['entity'] = SubProject.objects.get(id=object_id)
                context['entity_type'] = 'subproject'
            elif content_type.model == 'chargingstation':
                context['entity'] = ChargingStation.objects.get(id=object_id)
                context['entity_type'] = 'chargingstation'
        
        # Placeholder values
        context['placeholder_values'] = report.placeholder_values.all()
        
        return context

class ReportCreateView(LoginRequiredMixin, CreateView):
    """Vista per creare un nuovo report"""
    model = Report
    form_class = ReportForm
    template_name = 'reporting/report_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Per il form di selezione template
        context['templates'] = ReportTemplate.objects.all()
        context['report_types'] = ReportType.choices
        
        # Se è specificata un'entità nella URL
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
    
    def form_valid(self, form):
        # Salva il report
        self.object = form.save()
        
        # Avvia la generazione del report in background
        if settings.USE_CELERY:
            # Usa Celery se configurato
            generate_report_task.delay(self.object.id)
        else:
            # Altrimenti esegui in modo sincrono
            success, message = generate_report_async(self.object.id)
            if not success:
                messages.error(self.request, _('Errore nella generazione del report: {0}').format(message))
        
        messages.success(self.request, _('Report creato con successo. La generazione è in corso.'))
        return redirect('reporting:report_detail', pk=self.object.pk)
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Precompila il form se l'entità è specificata nella URL
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            initial['entity_type'] = entity_type
            
            if entity_type == 'project':
                initial['project'] = entity_id
            elif entity_type == 'subproject':
                initial['subproject'] = entity_id
            elif entity_type == 'chargingstation':
                initial['chargingstation'] = entity_id
                
        return initial

class ReportDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista per eliminare un report"""
    model = Report
    template_name = 'reporting/report_confirm_delete.html'
    permission_required = 'reporting.delete_report'
    success_url = reverse_lazy('reporting:report_list')
    
    def delete(self, request, *args, **kwargs):
        report = self.get_object()
        
        # Elimina il file PDF se esiste
        if report.generated_file:
            try:
                if os.path.isfile(report.generated_file.path):
                    os.remove(report.generated_file.path)
            except Exception as e:
                pass
        
        messages.success(request, _('Report eliminato con successo.'))
        return super().delete(request, *args, **kwargs)

class ReportBulkCreateView(LoginRequiredMixin, FormView):
    """Vista per creare report in blocco"""
    template_name = 'reporting/report_bulk_create.html'
    form_class = ReportFilterForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Lista dei template disponibili
        context['templates'] = ReportTemplate.objects.all()
        
        # Entità disponibili
        context['projects'] = Project.objects.all()
        context['subprojects'] = SubProject.objects.all()
        context['charging_stations'] = ChargingStation.objects.all()
        
        return context
    
    def form_valid(self, form):
        template_id = self.request.POST.get('template')
        entity_type = self.request.POST.get('entity_type')
        entity_ids = self.request.POST.getlist('entity_ids')
        
        if not template_id:
            messages.error(self.request, _('Seleziona un template valido.'))
            return self.form_invalid(form)
        
        # Genera i report
        count, report_ids = generate_bulk_reports(
            template_id=template_id,
            entity_type=entity_type,
            entity_ids=entity_ids if entity_ids else None,
            created_by=self.request.user
        )
        
        if count > 0:
            # Avvia la generazione dei report in background
            if settings.USE_CELERY:
                for report_id in report_ids:
                    generate_report_task.delay(report_id)
            else:
                # In modo sincrono, genera solo il primo report
                if report_ids:
                    success, message = generate_report_async(report_ids[0])
                    if not success:
                        messages.error(self.request, _('Errore nella generazione del report: {0}').format(message))
            
            messages.success(
                self.request, 
                _('Creati {0} report. La generazione è in corso.').format(count)
            )
        else:
            messages.error(self.request, _('Nessun report creato.'))
            
        return redirect('reporting:report_list')

class RegenerateReportView(LoginRequiredMixin, DetailView):
    """Vista per rigenerare un report esistente"""
    model = Report
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        report = self.get_object()
        
        # Avvia la rigenerazione
        if settings.USE_CELERY:
            generate_report_task.delay(report.id)
        else:
            success, message = generate_report_async(report.id)
            if not success:
                messages.error(request, _('Errore nella rigenerazione del report: {0}').format(message))
                
        messages.success(request, _('Rigenerazione del report avviata.'))
        return redirect('reporting:report_detail', pk=report.pk)

class DownloadReportView(LoginRequiredMixin, DetailView):
    """Vista per scaricare un report generato"""
    model = Report
    
    def get(self, request, *args, **kwargs):
        report = self.get_object()
        
        if not report.generated_file:
            messages.error(request, _('Il report non è ancora stato generato.'))
            return redirect('reporting:report_detail', pk=report.pk)
            
        try:
            with open(report.generated_file.path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(report.generated_file.name)}"'
                return response
        except Exception as e:
            messages.error(request, _('Errore nel download del file: {0}').format(str(e)))
            return redirect('reporting:report_detail', pk=report.pk)

class ReportPreviewView(LoginRequiredMixin, DetailView):
    """Vista per visualizzare l'anteprima di un report"""
    model = Report
    template_name = 'reporting/report_preview.html'
    context_object_name = 'report'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()
        
        if not report.generated_file:
            context['error'] = _('Il report non è ancora stato generato.')
        else:
            context['pdf_url'] = report.generated_file.url
            
        return context

def report_status_api(request, pk):
    """API per verificare lo stato di generazione di un report"""
    if not request.is_ajax():
        return JsonResponse({'error': 'Invalid request'}, status=400)
        
    try:
        report = Report.objects.get(pk=pk)
        return JsonResponse({
            'status': report.status,
            'is_generating': report.is_generating,
            'has_error': bool(report.generation_error),
            'error_message': report.generation_error,
            'file_url': report.file_url if report.generated_file else None
        })
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found'}, status=404)