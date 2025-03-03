# reporting/services.py
import os
import tempfile
import json
import logging
from datetime import datetime
from django.conf import settings
from django.core.files import File
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Sum, Avg, Max, Min, Count
from django.contrib.contenttypes.models import ContentType
from weasyprint import HTML, CSS
from jinja2 import Template, Environment, FileSystemLoader

from cpo_planner.projects.models import (
    Project, SubProject, ChargingStation, 
    FinancialProjection, YearlyProjection
)
from .models import Report, ReportPlaceholderValue, ReportType

# Configura il logger
logger = logging.getLogger(__name__)

class ReportGenerator:
    """Classe per generare report PDF"""
    
    def __init__(self, report_id):
        """Inizializza il generatore con l'ID del report"""
        self.report = Report.objects.get(id=report_id)
        self.template = self.report.template
        self.data = {}
        
    def generate(self):
        """Genera il report"""
        try:
            # Segna il report come in generazione
            self.report.mark_as_generating()
            
            # Prepara i dati
            self._prepare_data()
            
            # Genera il PDF
            pdf_path = self._generate_pdf()
            
            # Aggiorna il report con il file generato
            self.report.mark_as_completed(pdf_path)
            
            return True, self.report.file_url
            
        except Exception as e:
            logger.error(f"Errore nella generazione del report {self.report.id}: {str(e)}")
            self.report.mark_as_failed(str(e))
            return False, str(e)
    
    def _prepare_data(self):
        """Prepara i dati per il report"""
        # Dati di base
        self.data = {
            'report_title': self.report.title,
            'report_description': self.report.description,
            'generated_at': timezone.now().strftime('%d/%m/%Y %H:%M'),
            'generated_by': self.report.created_by.get_full_name(),
        }
        
        # Aggiungi i valori dei placeholder
        placeholder_values = self.report.placeholder_values.all()
        for pv in placeholder_values:
            self.data[pv.placeholder.name] = pv.value
        
        # Aggiungi valori predefiniti per placeholder senza valori specifici
        all_placeholders = self.template.placeholders.all()
        for placeholder in all_placeholders:
            if placeholder.name not in self.data:
                self.data[placeholder.name] = placeholder.default_value
        
        # Aggiungi dati specifici in base al tipo di entità
        if self.report.content_type and self.report.object_id:
            self._add_entity_data()
        
        # Aggiungi dati specifici in base al tipo di report
        report_type = self.template.type
        if report_type == ReportType.BUSINESS_PLAN:
            self._add_business_plan_data()
        elif report_type == ReportType.FINANCIAL_REPORT:
            self._add_financial_report_data()
        elif report_type == ReportType.PROJECT_OVERVIEW:
            self._add_project_overview_data()
        elif report_type == ReportType.MUNICIPAL_APPROVAL:
            self._add_municipal_approval_data()
        elif report_type == ReportType.CHARGING_STATION_SPECS:
            self._add_charging_station_data()
    
    def _add_entity_data(self):
        """Aggiunge dati specifici dell'entità"""
        content_type = self.report.content_type
        object_id = self.report.object_id
        
        if content_type.model == 'project':
            self._add_project_data(Project.objects.get(id=object_id))
        elif content_type.model == 'subproject':
            self._add_subproject_data(SubProject.objects.get(id=object_id))
        elif content_type.model == 'chargingstation':
            self._add_charging_station_data(ChargingStation.objects.get(id=object_id))
    
    def _add_project_data(self, project):
        """Aggiunge dati specifici del progetto"""
        self.data.update({
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'start_date': project.start_date.strftime('%d/%m/%Y') if project.start_date else '',
                'end_date': project.end_date.strftime('%d/%m/%Y') if project.end_date else '',
                'status': project.get_status_display(),
                'budget': project.budget,
                'subprojects_count': project.subprojects.count(),
                'stations_count': ChargingStation.objects.filter(subproject__project=project).count()
            }
        })
        
        # Aggiungi dati finanziari
        self._add_project_financial_data(project)
        
        # Aggiungi dati dei sotto-progetti
        subprojects = []
        for subproject in project.subprojects.all():
            subprojects.append({
                'id': subproject.id,
                'name': subproject.name,
                'description': subproject.description,
                'municipality': subproject.municipality.name if subproject.municipality else '',
                'status': subproject.get_status_display(),
                'budget': subproject.budget,
                'stations_count': subproject.charging_stations.count()
            })
        
        self.data['subprojects'] = subprojects
    
    def _add_subproject_data(self, subproject):
        """Aggiunge dati specifici del sotto-progetto"""
        self.data.update({
            'subproject': {
                'id': subproject.id,
                'name': subproject.name,
                'description': subproject.description,
                'municipality': subproject.municipality.name if subproject.municipality else '',
                'status': subproject.get_status_display(),
                'budget': subproject.budget,
                'project_name': subproject.project.name if subproject.project else '',
                'stations_count': subproject.charging_stations.count()
            }
        })
        
        # Aggiungi dati del progetto principale
        if subproject.project:
            self._add_project_data(subproject.project)
        
        # Aggiungi dati delle stazioni di ricarica
        stations = []
        for station in subproject.charging_stations.all():
            stations.append({
                'id': station.id,
                'name': station.name,
                'location': station.location,
                'address': station.address,
                'power': station.power,
                'connectors': station.connectors,
                'status': station.get_status_display(),
                'installation_cost': station.installation_cost,
                'operational_cost': station.operational_cost,
            })
        
        self.data['charging_stations'] = stations
    
    def _add_charging_station_data(self, station=None):
        """Aggiunge dati specifici della stazione di ricarica"""
        if station is None:
            # Se chiamato dal tipo di report, non da una specifica stazione
            return
            
        self.data.update({
            'charging_station': {
                'id': station.id,
                'name': station.name,
                'location': station.location,
                'address': station.address,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'power': station.power,
                'connectors': station.connectors,
                'charging_points': station.charging_points,
                'status': station.get_status_display(),
                'installation_cost': station.installation_cost,
                'operational_cost': station.operational_cost,
                'installation_date': station.installation_date.strftime('%d/%m/%Y') if station.installation_date else '',
                'subproject_name': station.subproject.name if station.subproject else '',
                'project_name': station.subproject.project.name if station.subproject and station.subproject.project else '',
                'municipality': station.subproject.municipality.name if station.subproject and station.subproject.municipality else '',
            }
        })
        
        # Aggiungi dati del sotto-progetto
        if station.subproject:
            self._add_subproject_data(station.subproject)
    
    def _add_project_financial_data(self, project):
        """Aggiunge dati finanziari del progetto"""
        try:
            # Ottieni la proiezione finanziaria più recente
            financial_projection = FinancialProjection.objects.filter(
                project=project
            ).order_by('-created_at').first()
            
            if financial_projection:
                yearly_projections = []
                for yp in financial_projection.yearly_projections.all().order_by('year'):
                    yearly_projections.append({
                        'year': yp.year,
                        'revenue': yp.revenue,
                        'cost': yp.cost,
                        'profit': yp.profit,
                        'cumulative_profit': yp.cumulative_profit,
                        'roi': yp.roi
                    })
                
                self.data['financial_projection'] = {
                    'id': financial_projection.id,
                    'name': financial_projection.name,
                    'description': financial_projection.description,
                    'total_investment': financial_projection.total_investment,
                    'total_revenue': financial_projection.total_revenue,
                    'total_cost': financial_projection.total_cost,
                    'total_profit': financial_projection.total_profit,
                    'roi': financial_projection.roi,
                    'payback_period': financial_projection.payback_period,
                    'yearly_projections': yearly_projections
                }
        except Exception as e:
            logger.error(f"Errore nell'ottenere i dati finanziari: {str(e)}")
        
    def _add_business_plan_data(self):
        """Aggiunge dati specifici per i business plan"""
        # Questi dati variano in base al tipo di entità e sono già stati aggiunti
        pass
    
    def _add_financial_report_data(self):
        """Aggiunge dati specifici per i report finanziari"""
        # Questi dati variano in base al tipo di entità e sono già stati aggiunti
        pass
    
    def _add_project_overview_data(self):
        """Aggiunge dati per la panoramica del progetto"""
        # Questi dati variano in base al tipo di entità e sono già stati aggiunti
        pass
    
    def _add_municipal_approval_data(self):
        """Aggiunge dati per la documentazione comunale"""
        # Se non collegato a nessuna entità specifica, aggiungi dati globali
        if not self.report.content_type:
            return
            
        # Se collegato a un progetto, aggiungi dati dei comuni coinvolti
        if self.report.content_type.model == 'project':
            project = Project.objects.get(id=self.report.object_id)
            municipalities = {}
            
            for subproject in project.subprojects.all():
                if subproject.municipality:
                    municipality_name = subproject.municipality.name
                    if municipality_name not in municipalities:
                        municipalities[municipality_name] = {
                            'name': municipality_name,
                            'stations_count': 0,
                            'total_power': 0,
                            'stations': []
                        }
                    
                    for station in subproject.charging_stations.all():
                        municipalities[municipality_name]['stations_count'] += 1
                        municipalities[municipality_name]['total_power'] += station.power or 0
                        municipalities[municipality_name]['stations'].append({
                            'name': station.name,
                            'location': station.location,
                            'address': station.address,
                            'power': station.power,
                            'connectors': station.connectors
                        })
                        
            self.data['municipalities'] = list(municipalities.values())
            
        # Se collegato a un sotto-progetto, aggiungi dati del comune
        elif self.report.content_type.model == 'subproject':
            subproject = SubProject.objects.get(id=self.report.object_id)
            if subproject.municipality:
                stations = []
                total_power = 0
                
                for station in subproject.charging_stations.all():
                    stations.append({
                        'name': station.name,
                        'location': station.location,
                        'address': station.address,
                        'power': station.power,
                        'connectors': station.connectors
                    })
                    total_power += station.power or 0
                
                self.data['municipality'] = {
                    'name': subproject.municipality.name,
                    'stations_count': len(stations),
                    'total_power': total_power,
                    'stations': stations
                }
    
    def _generate_pdf(self):
        """Genera il PDF dal template"""
        # Ottieni il percorso del template
        template_path = self.template.template_file.path
        template_dir = os.path.dirname(template_path)
        template_file = os.path.basename(template_path)
        
        # Imposta l'ambiente Jinja2
        env = Environment(loader=FileSystemLoader(template_dir))
        template = env.get_template(template_file)
        
        # Rendering del template HTML
        html_content = template.render(**self.data)
        
        # Crea file temporaneo per il PDF
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            # Genera PDF con WeasyPrint
            css = None
            if self.template.css:
                css_file = tempfile.NamedTemporaryFile(suffix='.css', delete=False)
                css_file.write(self.template.css.encode('utf-8'))
                css_file.close()
                css = CSS(filename=css_file.name)
            
            HTML(string=html_content).write_pdf(tmp.name, stylesheets=[css] if css else None)
            
            # Crea il percorso per il file
            filename = f"report_{self.report.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            report_path = os.path.join('reports', filename)
            
            # Salva il file nel file system di Django
            with open(tmp.name, 'rb') as f:
                self.report.generated_file.save(report_path, File(f), save=True)
                
            return report_path

# Funzione helper per generare report in background
def generate_report_async(report_id):
    """Genera un report in modalità asincrona"""
    generator = ReportGenerator(report_id)
    return generator.generate()

# Funzione per generare una collezione di report (es. per tutti i progetti o stazioni)
def generate_bulk_reports(template_id, entity_type=None, entity_ids=None, created_by=None):
    """
    Genera report in blocco per più entità
    
    Args:
        template_id: ID del template da utilizzare
        entity_type: Tipo di entità ('project', 'subproject', 'chargingstation')
        entity_ids: Lista di ID delle entità (se None, usa tutte le entità del tipo)
        created_by: Utente che sta creando i report
        
    Returns:
        tuple: (numero di report creati, lista di ID dei report)
    """
    from django.db import transaction
    
    try:
        # Ottieni il template
        template = ReportTemplate.objects.get(id=template_id)
        report_ids = []
        
        with transaction.atomic():
            # Determina le entità da processare
            if entity_type == 'project':
                model = Project
                content_type = ContentType.objects.get_for_model(Project)
            elif entity_type == 'subproject':
                model = SubProject
                content_type = ContentType.objects.get_for_model(SubProject)
            elif entity_type == 'chargingstation':
                model = ChargingStation
                content_type = ContentType.objects.get_for_model(ChargingStation)
            else:
                # Nessuna entità specificata, crea un singolo report globale
                report = Report.objects.create(
                    title=f"{template.name} - {timezone.now().strftime('%d/%m/%Y')}",
                    description=template.description,
                    template=template,
                    created_by=created_by
                )
                report_ids.append(report.id)
                return 1, report_ids
            
            # Filtra per ID specifici se forniti
            if entity_ids:
                entities = model.objects.filter(id__in=entity_ids)
            else:
                entities = model.objects.all()
            
            # Crea un report per ogni entità
            for entity in entities:
                report = Report.objects.create(
                    title=f"{template.name} - {entity.name}",
                    description=f"{template.description} per {entity.name}",
                    template=template,
                    content_type=content_type,
                    object_id=entity.id,
                    created_by=created_by
                )
                report_ids.append(report.id)
            
            return len(report_ids), report_ids
            
    except Exception as e:
        logger.error(f"Errore nella creazione di report in blocco: {str(e)}")
        return 0, []