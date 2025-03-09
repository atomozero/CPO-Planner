# reporting/views.py
import os
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse, Http404, FileResponse
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.core.paginator import Paginator
from io import BytesIO

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

@login_required
def generate_charging_station_installation_report(request, pk):
    """Genera un report di installazione per la stazione di ricarica con un design completamente rinnovato"""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, Flowable
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm, mm
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.graphics.shapes import Drawing, Line
    
    # Importa entrambi i modelli SubProject da diversi moduli
    from cpo_planner.projects.models import SubProject as ProjectsSubProject
    from cpo_core.models.subproject import SubProject as CoreSubProject
    
    # Classe personalizzata per i separatori con stile moderno
    class HorizontalLine(Flowable):
        def __init__(self, width, height=0.5, color=colors.grey):
            Flowable.__init__(self)
            self.width = width
            self.height = height
            self.color = color
        
        def draw(self):
            self.canv.setStrokeColor(self.color)
            self.canv.setLineWidth(self.height)
            self.canv.line(0, 0, self.width, 0)
    
    # Crea il buffer per il PDF
    buffer = BytesIO()
    
    try:
        # Verifica prima se esiste una ChargingStation con questo ID
        station = None
        is_subproject = False
        from_core = False
        
        try:
            station = ChargingStation.objects.get(pk=pk)
        except ChargingStation.DoesNotExist:
            # Se non esiste una ChargingStation, prova con SubProject da cpo_planner
            try:
                station = ProjectsSubProject.objects.get(pk=pk)
                is_subproject = True
            except ProjectsSubProject.DoesNotExist:
                # Se non esiste, prova con SubProject da cpo_core
                try:
                    station = CoreSubProject.objects.get(pk=pk)
                    is_subproject = True
                    from_core = True
                except CoreSubProject.DoesNotExist:
                    # Se non esiste né una ChargingStation né un SubProject, solleva un'eccezione
                    raise Http404("Stazione di ricarica non trovata")
        
        # Prepara i dati in base al tipo di oggetto
        if is_subproject:
            # Se è un SubProject, usa i suoi campi
            station_name = station.name
            address = station.address
            
            # Coordinate GPS
            latitude = station.latitude_approved if station.latitude_approved else station.latitude_proposed
            longitude = station.longitude_approved if station.longitude_approved else station.longitude_proposed
            
            # Marca della colonnina
            brand = station.charger_brand
            model = station.charger_model
            
            # Potenza
            power = station.power_kw
            
            # Connettori
            connector_types = station.connector_types
            num_connectors = station.num_connectors
            
            # Descrizione
            description = station.description
            
            # Date
            start_date = station.start_date
            
            # Gestisci le differenze tra i due modelli
            if from_core:
                # SubProject da cpo_core.models.subproject
                end_date = station.planned_completion_date if hasattr(station, 'planned_completion_date') else None
            else:
                # SubProject da cpo_planner.projects.models.subproject
                end_date = station.expected_completion_date if hasattr(station, 'expected_completion_date') else None
            
            # Modem 4G (assunto come No per i SubProject)
            has_4g = False
            
            # Riferimenti
            project = station.project
            municipality = station.municipality
        else:
            # Se è una ChargingStation, usa i suoi campi
            station_name = station.name
            
            # Indirizzo
            address = station.address if hasattr(station, 'address') and station.address else station.location if hasattr(station, 'location') else None
            
            # Coordinate GPS
            latitude = station.latitude if hasattr(station, 'latitude') else None
            longitude = station.longitude if hasattr(station, 'longitude') else None
            
            # Marca della colonnina
            brand = station.brand if hasattr(station, 'brand') and station.brand else (station.subproject.charger_brand if hasattr(station, 'subproject') and hasattr(station.subproject, 'charger_brand') else None)
            model = station.subproject.charger_model if hasattr(station, 'subproject') and hasattr(station.subproject, 'charger_model') else None
            
            # Potenza
            power = station.power_kw if hasattr(station, 'power_kw') else (station.max_power if hasattr(station, 'max_power') else None)
            
            # Connettori
            connector_types = station.connector_types if hasattr(station, 'connector_types') else None
            num_connectors = station.num_connectors if hasattr(station, 'num_connectors') else None
            
            # Descrizione
            description = station.notes if hasattr(station, 'notes') else None
            
            # Date
            start_date = station.subproject.start_date if hasattr(station, 'subproject') and hasattr(station.subproject, 'start_date') else None
            end_date = station.subproject.expected_completion_date if hasattr(station, 'subproject') and hasattr(station.subproject, 'expected_completion_date') else None
            
            # Modem 4G
            has_4g = hasattr(station, 'modem_4g_cost') and station.modem_4g_cost > 0
            
            # Potenza richiesta
            power_requested = None
            if hasattr(station, 'grid_connection_capacity') and station.grid_connection_capacity:
                power_requested = station.grid_connection_capacity
            elif hasattr(station, 'subproject') and hasattr(station.subproject, 'power_requested') and station.subproject.power_requested:
                power_requested = station.subproject.power_requested
                
            # Riferimenti
            project = station.subproject.project if hasattr(station, 'subproject') and hasattr(station.subproject, 'project') else None
            municipality = station.subproject.municipality if hasattr(station, 'subproject') and hasattr(station.subproject, 'municipality') else None
        
        # Definizione colori moderni
        brand_color = colors.HexColor("#0066CC")      # Blu primario
        accent_color = colors.HexColor("#FF6600")     # Arancione accent
        bg_light = colors.HexColor("#F5F7FA")         # Grigio chiaro
        text_dark = colors.HexColor("#333333")        # Grigio scuro per il testo
        text_light = colors.HexColor("#777777")       # Grigio chiaro per dettagli
        success_color = colors.HexColor("#4CAF50")    # Verde
        
        # Crea il documento PDF con margini ottimizzati
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15*mm,
            leftMargin=15*mm,
            topMargin=15*mm,
            bottomMargin=15*mm,
            title=f"Scheda Installazione - {station_name}"
        )
        
        # Stili moderni
        styles = getSampleStyleSheet()
        
        # Stile per il titolo principale
        title_style = ParagraphStyle(
            name='TitleModern',
            fontName='Helvetica-Bold',
            fontSize=24,  # Dimensione maggiore per dare più importanza
            leading=30,
            textColor=brand_color,
            alignment=TA_LEFT,
            spaceAfter=1*mm,
        )
        
        # Stile per il sottotitolo
        subtitle_style = ParagraphStyle(
            name='SubtitleModern',
            fontName='Helvetica',
            fontSize=16,  # Dimensione maggiore per il sottotitolo
            leading=20,
            textColor=text_dark,  # Colore più scuro per migliorare il contrasto
            alignment=TA_LEFT,
        )
        
        # Stile per le intestazioni di sezione
        section_title_style = ParagraphStyle(
            name='SectionModern',
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=brand_color,
            spaceBefore=2*mm,  # Ridotto da 10*mm a 2*mm
            spaceAfter=5*mm,
        )
        
        # Stile per il testo normale
        normal_style = ParagraphStyle(
            name='NormalModern',
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_dark,
        )
        
        # Stile per le etichette
        label_style = ParagraphStyle(
            name='LabelModern',
            fontName='Helvetica-Bold',
            fontSize=10,
            leading=14,
            textColor=text_dark,
        )
        
        # Stile per i valori
        value_style = ParagraphStyle(
            name='ValueModern',
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=text_dark,
        )
        
        # Stile per il footer
        footer_style = ParagraphStyle(
            name='FooterModern',
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=text_light,
        )
        
        # Prepara le immagini
        project_logo = None
        municipality_logo = None
        charger_image = None
        
        # Logo del progetto (se disponibile)
        if project and hasattr(project, 'logo') and project.logo:
            try:
                from PIL import Image as PILImage
                project_logo_path = project.logo.path
                
                # Apri l'immagine con PIL per ottenere le dimensioni originali
                pil_img = PILImage.open(project_logo_path)
                img_width, img_height = pil_img.size
                
                # Calcola il rapporto di aspetto
                aspect_ratio = img_height / float(img_width)
                
                # Imposta la larghezza desiderata
                desired_width = 6*cm
                
                # Calcola l'altezza in base al rapporto di aspetto
                calculated_height = desired_width * aspect_ratio
                
                # Crea l'immagine mantenendo il rapporto di aspetto
                project_logo = Image(project_logo_path, width=desired_width, height=calculated_height)
            except Exception as e:
                print(f"Errore caricamento logo progetto: {e}")
                
        # Logo del comune (se disponibile)
        if municipality and hasattr(municipality, 'logo') and municipality.logo:
            try:
                from PIL import Image as PILImage
                municipality_logo_path = municipality.logo.path
                
                # Apri l'immagine con PIL per ottenere le dimensioni originali
                pil_img = PILImage.open(municipality_logo_path)
                img_width, img_height = pil_img.size
                
                # Calcola il rapporto di aspetto
                aspect_ratio = img_height / float(img_width)
                
                # Imposta la larghezza desiderata
                desired_width = 3*cm
                
                # Calcola l'altezza in base al rapporto di aspetto
                calculated_height = desired_width * aspect_ratio
                
                # Crea l'immagine mantenendo il rapporto di aspetto
                municipality_logo = Image(municipality_logo_path, width=desired_width, height=calculated_height)
            except Exception as e:
                print(f"Errore caricamento logo comune: {e}")
        
        # Elementi del documento
        elements = []
        
        # INTESTAZIONE MODERNA RIVISITATA
        # Prima il logo del progetto, poi il titolo con il logo del comune a destra
        
        # Aggiungiamo il logo del progetto sopra a tutto
        if project_logo:
            logo_project_table = Table([[project_logo]], colWidths=[doc.width])
            logo_project_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'CENTER'),
                ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (0, 0), 0),
                ('BOTTOMPADDING', (0, 0), (0, 0), 10),
            ]))
            elements.append(logo_project_table)
            elements.append(Spacer(1, 5*mm))
        
        # Titolo principale e sottotitolo in una tabella, con logo del comune a destra
        title_text = Paragraph(f"Scheda Installazione", title_style)
        subtitle_text = Paragraph(f"{station_name}", subtitle_style)
        
        # Struttura per il titolo e sottotitolo
        if municipality_logo:
            # Creiamo una tabella con titolo e sottotitolo insieme a sinistra
            title_column_data = [
                [title_text],
                [subtitle_text]
            ]
            
            # Riduzione dello spazio tra titolo e sottotitolo
            title_column = Table(title_column_data, colWidths=[doc.width-(4*cm)])
            title_column.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (0, 0), 0),  # Ridotto il padding sotto il titolo
                ('TOPPADDING', (0, 1), (0, 1), 0),     # Ridotto il padding sopra il sottotitolo
            ]))
            
            # Tabella principale con la colonna del titolo a sinistra e logo comune a destra
            main_row = [[title_column, municipality_logo]]
            main_widths = [doc.width-(4*cm), 4*cm]
            main_table = Table(main_row, colWidths=main_widths)
            main_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, 0), 'LEFT'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
            ]))
            
            elements.append(main_table)
        else:
            # Se non c'è il logo del comune, tabella semplice con titolo e sottotitolo ravvicinati
            title_subtable_data = [
                [title_text],
                [subtitle_text],
            ]
            
            title_subtable = Table(title_subtable_data, colWidths=[doc.width])
            title_subtable.setStyle(TableStyle([
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (0, 0), 0),  # Ridotto il padding sotto il titolo
                ('TOPPADDING', (0, 1), (0, 1), 0),     # Ridotto il padding sopra il sottotitolo
            ]))
            
            elements.append(title_subtable)
        elements.append(Spacer(1, 3*mm))
        
        # Linea separatrice dopo titolo e logo comune
        elements.append(HorizontalLine(width=doc.width, color=accent_color))
        elements.append(Spacer(1, 8*mm))
        
        # Spazio dopo l'intestazione
        elements.append(Spacer(1, 8*mm))
        
        # Sezione INFO GENERALI
        # Riduciamo lo spazio aggiuntivo prima del titolo della sezione
        elements.append(Paragraph("Informazioni Generali", section_title_style))
        elements.append(HorizontalLine(width=doc.width, color=brand_color))
        elements.append(Spacer(1, 3*mm))
        
        # Layout a 2 colonne con immagine a destra
        
        # Colonna sinistra: informazioni generali
        info_data = []
        
        # Funzione helper per creare righe con stile
        def styled_row(label, value, is_bold=False):
            if value is None or value == '':
                value = '-'
            
            if is_bold:
                return [
                    Paragraph(f'<b>{label}</b>', label_style),
                    Paragraph(f'<b>{value}</b>', value_style)
                ]
            return [
                Paragraph(f'{label}', label_style),
                Paragraph(f'{value}', value_style)
            ]
        
        # Aggiunge righe alla tabella info
        if address:
            info_data.append(styled_row("Indirizzo:", address))
            
        if latitude and longitude:
            info_data.append(styled_row("Coordinate GPS:", f"Lat: {latitude}, Long: {longitude}"))
            
        if brand:
            info_data.append(styled_row("Marca Colonnina:", brand))
            
        if model:
            info_data.append(styled_row("Modello Colonnina:", model))
            
        info_data.append(styled_row("Modem 4G:", "Sì" if has_4g else "No"))
        
        if power:
            info_data.append(styled_row("Potenza:", f"{power} kW", True))
        
        # Potenza richiesta
        power_requested_value = None
        if is_subproject:
            power_requested = station.power_kw
            if power_requested:
                power_requested_value = f"{power_requested} kW"
        else:
            if hasattr(station, 'grid_connection_capacity') and station.grid_connection_capacity:
                power_requested_value = f"{station.grid_connection_capacity} kW"
            elif hasattr(station, 'subproject') and hasattr(station.subproject, 'power_requested') and station.subproject.power_requested:
                power_requested_value = f"{station.subproject.power_requested} kW"
        
        if power_requested_value:
            info_data.append(styled_row("Potenza Richiesta:", power_requested_value))
        
        # Descrizione
        if description:
            info_data.append(styled_row("Descrizione:", description))
            
        # Date
        if start_date:
            info_data.append(styled_row("Data Inizio Lavori:", start_date.strftime('%d/%m/%Y')))
            
        if end_date:
            info_data.append(styled_row("Data Prevista Fine Lavori:", end_date.strftime('%d/%m/%Y')))
        
        # Stile moderno per la tabella info
        info_table = Table(info_data, colWidths=[150, 400])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.15, colors.lightgrey),
            ('BACKGROUND', (0, 0), (0, -1), bg_light),
        ]))
        
        # Aggiungiamo la tabella info a tutta larghezza
        elements.append(info_table)
        
        # SPECIFICHE TECNICHE
        elements.append(Spacer(1, 10*mm))
        elements.append(Paragraph("Specifiche Tecniche", section_title_style))
        elements.append(HorizontalLine(width=doc.width, color=brand_color))
        elements.append(Spacer(1, 3*mm))
        
        tech_data = []
        
        # Tipo di connessione
        if not is_subproject and hasattr(station, 'connection_type') and station.connection_type:
            tech_data.append(styled_row("Tipo di Connessione:", station.get_connection_type_display()))
        elif not is_subproject and hasattr(station, 'power_type') and station.power_type:
            tech_data.append(styled_row("Tipo di Alimentazione:", station.get_power_type_display()))
            
        # Potenza massima
        if power:
            tech_data.append(styled_row("Potenza Massima:", f"{power} kW", True))
            
        # Numero di connettori
        if num_connectors:
            tech_data.append(styled_row("Numero di Connettori:", str(num_connectors)))
            
        # Tipi di connettori
        if connector_types:
            tech_data.append(styled_row("Tipi di Connettori:", connector_types))
            
        # Dati aggiuntivi sulla stazione
        if is_subproject:
            # Dati catastali se disponibili
            if hasattr(station, 'cadastral_data') and station.cadastral_data:
                tech_data.append(styled_row("Dati Catastali:", station.cadastral_data))
                
            # Profilo di utilizzo
            if hasattr(station, 'usage_profile') and station.usage_profile:
                tech_data.append(styled_row("Profilo di Utilizzo:", station.usage_profile.name if hasattr(station.usage_profile, 'name') else str(station.usage_profile)))
        
        # Informazioni sull'alimentazione e connessione elettrica
        if not is_subproject and hasattr(station, 'grid_connection_capacity'):
            tech_data.append(styled_row("Capacità Connessione Rete:", f"{station.grid_connection_capacity} kW"))
            
        # Area occupata dalla stazione
        if (is_subproject and hasattr(station, 'ground_area_sqm') and station.ground_area_sqm) or \
           (not is_subproject and hasattr(station, 'ground_area') and station.ground_area):
            area = station.ground_area_sqm if is_subproject else station.ground_area
            tech_data.append(styled_row("Area Occupata:", f"{area} m²"))
            
        # Caratteristiche di connettività e comunicazione
        if not is_subproject:
            if hasattr(station, 'has_lan') and station.has_lan:
                tech_data.append(styled_row("Connessione LAN:", "Sì"))
                
            if hasattr(station, 'has_wifi') and station.has_wifi:
                tech_data.append(styled_row("Connessione WiFi:", "Sì"))
                
        # Caratteristiche della colonnina (da Charger)
        if is_subproject and hasattr(station, 'chargers') and station.chargers.exists():
            charger = station.chargers.first()
            
            if hasattr(charger, 'is_fast_charging') and charger.is_fast_charging:
                tech_data.append(styled_row("Ricarica Rapida:", "Sì"))
                
            if hasattr(charger, 'is_smart_charging') and charger.is_smart_charging:
                tech_data.append(styled_row("Smart Charging:", "Sì"))
                
            if hasattr(charger, 'has_display') and charger.has_display:
                tech_data.append(styled_row("Display:", "Sì"))
                
            if hasattr(charger, 'has_rfid') and charger.has_rfid:
                tech_data.append(styled_row("Lettore RFID:", "Sì"))
                
            if hasattr(charger, 'has_app_control') and charger.has_app_control:
                tech_data.append(styled_row("Controllo App:", "Sì"))
        
        if tech_data:
            # Tabella specifiche tecniche con stile moderno
            tech_table = Table(tech_data, colWidths=[200, 340])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.15, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), bg_light),
            ]))
            elements.append(tech_table)
        
        # DATE IMPORTANTI
        dates_data = []
        
        # Date di installazione e attivazione (per ChargingStation)
        if not is_subproject:
            if hasattr(station, 'installation_date') and station.installation_date:
                dates_data.append(styled_row("Data di Installazione:", station.installation_date.strftime('%d/%m/%Y')))
                
            if hasattr(station, 'activation_date') and station.activation_date:
                dates_data.append(styled_row("Data di Attivazione:", station.activation_date.strftime('%d/%m/%Y')))
        
        # Date dal SubProject (alcune già incluse nella tabella generale)
        if is_subproject:
            if hasattr(station, 'start_date') and station.start_date:
                dates_data.append(styled_row("Data Inizio Lavori:", station.start_date.strftime('%d/%m/%Y')))
                
            if hasattr(station, 'planned_completion_date') and station.planned_completion_date:
                dates_data.append(styled_row("Data Prevista Completamento:", station.planned_completion_date.strftime('%d/%m/%Y')))
                
            if hasattr(station, 'actual_completion_date') and station.actual_completion_date:
                dates_data.append(styled_row("Data Effettiva Completamento:", station.actual_completion_date.strftime('%d/%m/%Y'), True))
            
            # Date cambio stato
            if hasattr(station, 'status_changed_date') and station.status_changed_date:
                dates_data.append(styled_row("Data Cambio Stato:", station.status_changed_date.strftime('%d/%m/%Y')))
        
        # Date per i Charger
        if is_subproject and hasattr(station, 'chargers') and station.chargers.exists():
            charger = station.chargers.first()
            
            if hasattr(charger, 'installation_date') and charger.installation_date:
                dates_data.append(styled_row("Data Installazione Colonnina:", charger.installation_date.strftime('%d/%m/%Y')))
                
            if hasattr(charger, 'activation_date') and charger.activation_date:
                dates_data.append(styled_row("Data Attivazione Colonnina:", charger.activation_date.strftime('%d/%m/%Y')))
        
        if dates_data:
            elements.append(Spacer(1, 10*mm))
            elements.append(Paragraph("Date Importanti", section_title_style))
            elements.append(HorizontalLine(width=doc.width, color=brand_color))
            elements.append(Spacer(1, 3*mm))
            
            # Tabella date con stile moderno
            dates_table = Table(dates_data, colWidths=[240, 300])
            dates_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.15, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), bg_light),
            ]))
            elements.append(dates_table)
        
        # RESPONSABILI E CONTATTI
        contacts_data = []
        
        if is_subproject and hasattr(station, 'responsible_person') and station.responsible_person:
            contacts_data.append(styled_row("Responsabile:", f"{station.responsible_person.first_name} {station.responsible_person.last_name}"))
            
            if hasattr(station, 'status_changed_by') and station.status_changed_by:
                contacts_data.append(styled_row("Ultimo Aggiornamento Stato:", f"{station.status_changed_by.first_name} {station.status_changed_by.last_name}"))
        
        if contacts_data:
            elements.append(Spacer(1, 10*mm))
            elements.append(Paragraph("Responsabili e Contatti", section_title_style))
            elements.append(HorizontalLine(width=doc.width, color=brand_color))
            elements.append(Spacer(1, 3*mm))
            
            # Tabella contatti con stile moderno
            contacts_table = Table(contacts_data, colWidths=[240, 300])
            contacts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 0), (-1, -1), text_dark),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.15, colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), bg_light),
            ]))
            elements.append(contacts_table)
        
        # FOOTER MODERNO
        elements.append(Spacer(1, 15*mm))
        
        # Linea separatrice
        elements.append(HorizontalLine(width=doc.width, color=text_light))
        elements.append(Spacer(1, 5*mm))
        
        # Informazioni del footer in stile moderno
        footer_data = [
            [
                Paragraph(f"Report generato il: {timezone.now().strftime('%d/%m/%Y')}", footer_style),
                Paragraph(f"Generato da: {request.user.get_full_name() or request.user.username}", footer_style),
            ]
        ]
        
        footer_table = Table(footer_data, colWidths=[doc.width/2, doc.width/2])
        footer_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (1, 0), text_light),
        ]))
        
        elements.append(footer_table)
        
        # Genera il PDF
        doc.build(elements)
        
        # Prepara la risposta
        buffer.seek(0)
        filename = f"Scheda_Installazione_{station_name.replace(' ', '_')}_{timezone.now().strftime('%Y%m%d')}.pdf"
        
        response = FileResponse(buffer, as_attachment=True, filename=filename)
        return response
        
    except Exception as e:
        messages.error(request, f"Errore nella generazione del report: {str(e)}")
        if 'HTTP_REFERER' in request.META:
            return redirect(request.META['HTTP_REFERER'])
        return redirect('reporting:report_list')