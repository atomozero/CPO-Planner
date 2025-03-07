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
    """Genera un report di installazione per la stazione di ricarica"""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    
    # Importa entrambi i modelli SubProject da diversi moduli
    from cpo_planner.projects.models import SubProject as ProjectsSubProject
    from cpo_core.models.subproject import SubProject as CoreSubProject
    
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
                
        # Crea il documento PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            title=f"Scheda Installazione - {station_name}"
        )
        
        # Stili
        styles = getSampleStyleSheet()
        
        # Crea stili con nomi unici per evitare conflitti
        title_style = ParagraphStyle(
            name='ReportTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
        )
        
        subtitle_style = ParagraphStyle(
            name='ReportSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
        )
        
        # Contenuto del report
        elements = []
        
        # Prepara le immagini
        project_logo = None
        municipality_logo = None
        charger_image = None
        
        # Logo del progetto (se disponibile)
        if project and hasattr(project, 'logo') and project.logo:
            try:
                project_logo_path = project.logo.path
                project_logo = Image(project_logo_path, width=3*cm, height=2*cm)
            except Exception as e:
                print(f"Errore caricamento logo progetto: {e}")
                
        # Logo del comune (se disponibile)
        if municipality and hasattr(municipality, 'logo') and municipality.logo:
            try:
                municipality_logo_path = municipality.logo.path
                municipality_logo = Image(municipality_logo_path, width=3*cm, height=2*cm)
            except Exception as e:
                print(f"Errore caricamento logo comune: {e}")
                
        # Immagine della colonnina (se disponibile)
        # Per SubProject: verifica se ci sono immagini collegate
        if is_subproject and hasattr(station, 'images') and station.images.exists():
            try:
                charger_image_obj = station.images.first()  # Prendi la prima immagine
                charger_image_path = charger_image_obj.image.path
                charger_image = Image(charger_image_path, width=5*cm, height=5*cm)
            except Exception as e:
                print(f"Errore caricamento immagine colonnina: {e}")
        # Per ChargingStation: verifica se c'è un'immagine collegata
        elif not is_subproject and hasattr(station, 'image') and station.image:
            try:
                charger_image_path = station.image.path
                charger_image = Image(charger_image_path, width=5*cm, height=5*cm)
            except Exception as e:
                print(f"Errore caricamento immagine colonnina: {e}")
        
        # Tabella di intestazione con loghi
        title_text = Paragraph(f"Scheda Installazione - {station_name}", title_style)
        header_data = [[project_logo or '', title_text, municipality_logo or '']]
        header_table = Table(header_data, colWidths=[3*cm, doc.width-6*cm, 3*cm])
        header_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 12))
        
        # Non abbiamo più bisogno di aggiungere il titolo qui poiché è già nell'intestazione
        
        # Informazioni sulla stazione
        elements.append(Paragraph("Informazioni Generali", subtitle_style))
        elements.append(Spacer(1, 6))
        
        # Prepara i dati per la tabella
        data = []
        
        # Indirizzo
        if address:
            data.append(["Indirizzo", address])
            
        # Coordinate GPS
        if latitude and longitude:
            data.append(["Coordinate GPS", f"Lat: {latitude}, Long: {longitude}"])
            
        # Marca della colonnina
        if brand:
            data.append(["Marca Colonnina", brand])
            
        # Modello della colonnina
        if model:
            data.append(["Modello Colonnina", model])
            
        # Modem 4G
        data.append(["Modem 4G", "Sì" if has_4g else "No"])
        
        # Potenza
        if power:
            data.append(["Potenza", f"{power} kW"])
            
        # Potenza richiesta
        if is_subproject:
            power_requested = station.power_kw  # Usa power_kw come potenza richiesta per i SubProject
            if power_requested:
                data.append(["Potenza Richiesta", f"{power_requested} kW"])
        else:
            # Per ChargingStation, usa grid_connection_capacity come già fatto
            power_requested = None
            if hasattr(station, 'grid_connection_capacity') and station.grid_connection_capacity:
                power_requested = station.grid_connection_capacity
            elif hasattr(station, 'subproject') and hasattr(station.subproject, 'power_requested') and station.subproject.power_requested:
                power_requested = station.subproject.power_requested
                
            if power_requested:
                data.append(["Potenza Richiesta", f"{power_requested} kW"])
            
        # Descrizione
        if description:
            data.append(["Descrizione", description])
            
        # Date
        # Data inizio lavori
        if start_date:
            data.append(["Data Inizio Lavori", start_date.strftime('%d/%m/%Y')])
            
        # Data fine lavori
        if end_date:
            data.append(["Data Prevista Fine Lavori", end_date.strftime('%d/%m/%Y')])
            
        # Crea sempre la tabella affiancata, indipendentemente dalla presenza dell'immagine
        # Specifica le larghezze delle colonne
        info_table = Table(data, colWidths=[150, 200])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        # Immagine segnaposto se non c'è l'immagine della colonnina
        placeholder_image = None
        if not charger_image:
            placeholder_image = Paragraph("", ParagraphStyle(name='Placeholder', spaceAfter=0))
        
        # Crea la tabella completa con info e immagine affiancate
        complete_data = [[info_table, charger_image or placeholder_image]]
        complete_table = Table(complete_data, colWidths=[350, 180])
        complete_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
            ('LEFTPADDING', (1, 0), (1, 0), 10),
        ]))
        
        elements.append(complete_table)
            
        # Specifiche tecniche (se disponibili)
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Specifiche Tecniche", subtitle_style))
        elements.append(Spacer(1, 6))
        
        tech_data = []
        
        # Tipo di connessione
        if not is_subproject and hasattr(station, 'connection_type') and station.connection_type:
            tech_data.append(["Tipo di Connessione", station.get_connection_type_display()])
        elif not is_subproject and hasattr(station, 'power_type') and station.power_type:
            tech_data.append(["Tipo di Alimentazione", station.get_power_type_display()])
            
        # Potenza massima
        if power:
            tech_data.append(["Potenza Massima", f"{power} kW"])
            
        # Numero di connettori
        if num_connectors:
            tech_data.append(["Numero di Connettori", str(num_connectors)])
            
        # Tipi di connettori
        if connector_types:
            tech_data.append(["Tipi di Connettori", connector_types])
            
        # Dati aggiuntivi sulla stazione
        if is_subproject:
            # Dati catastali se disponibili
            if hasattr(station, 'cadastral_data') and station.cadastral_data:
                tech_data.append(["Dati Catastali", station.cadastral_data])
                
            # Profilo di utilizzo
            if hasattr(station, 'usage_profile') and station.usage_profile:
                tech_data.append(["Profilo di Utilizzo", station.usage_profile.name if hasattr(station.usage_profile, 'name') else str(station.usage_profile)])
        
        # Informazioni sull'alimentazione e connessione elettrica
        if not is_subproject and hasattr(station, 'grid_connection_capacity'):
            tech_data.append(["Capacità Connessione Rete", f"{station.grid_connection_capacity} kW"])
            
        # Area occupata dalla stazione
        if (is_subproject and hasattr(station, 'ground_area_sqm') and station.ground_area_sqm) or \
           (not is_subproject and hasattr(station, 'ground_area') and station.ground_area):
            area = station.ground_area_sqm if is_subproject else station.ground_area
            tech_data.append(["Area Occupata", f"{area} m²"])
            
        # Caratteristiche di connettività e comunicazione
        if not is_subproject:
            if hasattr(station, 'has_lan') and station.has_lan:
                tech_data.append(["Connessione LAN", "Sì"])
                
            if hasattr(station, 'has_wifi') and station.has_wifi:
                tech_data.append(["Connessione WiFi", "Sì"])
                
        # Caratteristiche della colonnina (da Charger)
        if is_subproject and hasattr(station, 'chargers') and station.chargers.exists():
            charger = station.chargers.first()
            
            if hasattr(charger, 'is_fast_charging') and charger.is_fast_charging:
                tech_data.append(["Ricarica Rapida", "Sì"])
                
            if hasattr(charger, 'is_smart_charging') and charger.is_smart_charging:
                tech_data.append(["Smart Charging", "Sì"])
                
            if hasattr(charger, 'has_display') and charger.has_display:
                tech_data.append(["Display", "Sì"])
                
            if hasattr(charger, 'has_rfid') and charger.has_rfid:
                tech_data.append(["Lettore RFID", "Sì"])
                
            if hasattr(charger, 'has_app_control') and charger.has_app_control:
                tech_data.append(["Controllo App", "Sì"])
        
        if tech_data:
            tech_table = Table(tech_data, colWidths=[200, 250])
            tech_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(tech_table)
            
        # Rimuoviamo la sezione dei dettagli economici come richiesto
            
        # Date importanti
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Date Importanti", subtitle_style))
        elements.append(Spacer(1, 6))
        
        dates_data = []
        
        # Date di installazione e attivazione (per ChargingStation)
        if not is_subproject:
            if hasattr(station, 'installation_date') and station.installation_date:
                dates_data.append(["Data di Installazione", station.installation_date.strftime('%d/%m/%Y')])
                
            if hasattr(station, 'activation_date') and station.activation_date:
                dates_data.append(["Data di Attivazione", station.activation_date.strftime('%d/%m/%Y')])
        
        # Date dal SubProject (alcune già incluse nella tabella generale)
        if is_subproject:
            if hasattr(station, 'start_date') and station.start_date:
                dates_data.append(["Data Inizio Lavori", station.start_date.strftime('%d/%m/%Y')])
                
            if hasattr(station, 'planned_completion_date') and station.planned_completion_date:
                dates_data.append(["Data Prevista Completamento", station.planned_completion_date.strftime('%d/%m/%Y')])
                
            if hasattr(station, 'actual_completion_date') and station.actual_completion_date:
                dates_data.append(["Data Effettiva Completamento", station.actual_completion_date.strftime('%d/%m/%Y')])
            
            # Date cambio stato
            if hasattr(station, 'status_changed_date') and station.status_changed_date:
                dates_data.append(["Data Cambio Stato", station.status_changed_date.strftime('%d/%m/%Y')])
        
        # Date per i Charger
        if is_subproject and hasattr(station, 'chargers') and station.chargers.exists():
            charger = station.chargers.first()
            
            if hasattr(charger, 'installation_date') and charger.installation_date:
                dates_data.append(["Data Installazione Colonnina", charger.installation_date.strftime('%d/%m/%Y')])
                
            if hasattr(charger, 'activation_date') and charger.activation_date:
                dates_data.append(["Data Attivazione Colonnina", charger.activation_date.strftime('%d/%m/%Y')])
        
        if dates_data:
            dates_table = Table(dates_data, colWidths=[200, 250])
            dates_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(dates_table)
            
        # Informazioni responsabilità e contatti
        if is_subproject and hasattr(station, 'responsible_person') and station.responsible_person:
            elements.append(Spacer(1, 24))
            elements.append(Paragraph("Responsabili e Contatti", subtitle_style))
            elements.append(Spacer(1, 6))
            
            contacts_data = [
                ["Responsabile", f"{station.responsible_person.first_name} {station.responsible_person.last_name}"]
            ]
            
            if hasattr(station, 'status_changed_by') and station.status_changed_by:
                contacts_data.append(["Ultimo Aggiornamento Stato", f"{station.status_changed_by.first_name} {station.status_changed_by.last_name}"])
            
            contacts_table = Table(contacts_data, colWidths=[200, 250])
            contacts_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            elements.append(contacts_table)
        
        # Footer
        elements.append(Spacer(1, 36))
        elements.append(Paragraph(f"Report generato il: {timezone.now().strftime('%d/%m/%Y')}", styles['Normal']))
        elements.append(Paragraph(f"Generato da: {request.user.get_full_name() or request.user.username}", styles['Normal']))
        
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