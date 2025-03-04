# cpo_planner/projects/views/report_views.py
from django.views.generic import View, TemplateView
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, FileResponse
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.urls import reverse_lazy

import tempfile
import os
from weasyprint import HTML, CSS
from datetime import datetime

from ..models.project import Project
from ..models.charging_station import ChargingStation

class ProjectReportView(LoginRequiredMixin, View):
    """
    Vista per generare il business plan completo del progetto in PDF
    """
    def get(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        
        # Controlla se esiste un'analisi finanziaria
        try:
            financial_analysis = project.financial_analysis
        except:
            messages.warning(request, _('Prima di generare il report, esegui l\'analisi finanziaria!'))
            return redirect('projects:project_detail', pk=project_id)
        
        # Prepara il context
        context = {
            'project': project,
            'financial_analysis': financial_analysis,
            'subprojects': project.subproject_set.all(),
            'generated_at': datetime.now(),
            'user': request.user,
        }
        
        # Genera il contenuto HTML
        html_string = render_to_string('reports/project_business_plan.html', context)
        
        # Converti HTML in PDF
        html = HTML(string=html_string)
        
        # Crea file temporaneo
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            html.write_pdf(target=tmp.name)
            tmp_file = tmp.name
        
        # Prepara la risposta con il file PDF
        filename = f"business_plan_{project.name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        with open(tmp_file, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Elimina il file temporaneo
        os.unlink(tmp_file)
        
        return response

class StationReportView(LoginRequiredMixin, View):
    """
    Vista per generare la scheda della stazione di ricarica in PDF
    """
    def get(self, request, *args, **kwargs):
        station_id = self.kwargs.get('station_id')
        station = get_object_or_404(ChargingStation, pk=station_id)
        project_id = self.kwargs.get('project_id')
        
        # Controlla se esiste un'analisi finanziaria
        try:
            financial_analysis = station.financial_analysis
        except:
            messages.warning(request, _('Prima di generare il report, esegui l\'analisi finanziaria!'))
            return redirect('projects:station_detail', pk=station_id, project_id=project_id)
        
        # Controlla se esiste un cronoprogramma
        try:
            timeline = station.timeline
        except:
            timeline = None
        
        # Controlla se esiste un impianto fotovoltaico
        try:
            photovoltaic = station.photovoltaic_system
        except:
            photovoltaic = None
        
        # Prepara il context
        context = {
            'station': station,
            'subproject': station.sub_project,
            'project': station.sub_project.project,
            'financial_analysis': financial_analysis,
            'timeline': timeline,
            'photovoltaic': photovoltaic,
            'generated_at': datetime.now(),
            'user': request.user,
        }
        
        # Genera il contenuto HTML
        html_string = render_to_string('reports/station_report.html', context)
        
        # Converti HTML in PDF
        html = HTML(string=html_string)
        
        # Crea file temporaneo
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            html.write_pdf(target=tmp.name)
            tmp_file = tmp.name
        
        # Prepara la risposta con il file PDF
        filename = f"station_{station.identifier}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        with open(tmp_file, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Elimina il file temporaneo
        os.unlink(tmp_file)
        
        return response

class MunicipalityReportView(LoginRequiredMixin, View):
    """
    Vista per generare la documentazione da presentare al comune
    """
    def get(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        subproject_id = self.kwargs.get('subproject_id')
        
        from ..models.subproject import SubProject
        subproject = get_object_or_404(SubProject, pk=subproject_id)
        project = subproject.project
        municipality = subproject.municipality
        
        # Ottieni tutte le stazioni del sotto-progetto
        stations = subproject.chargingstation_set.all()
        
        # Prepara il context
        context = {
            'project': project,
            'subproject': subproject,
            'municipality': municipality,
            'stations': stations,
            'generated_at': datetime.now(),
            'user': request.user,
        }
        
        # Genera il contenuto HTML
        html_string = render_to_string('reports/municipality_report.html', context)
        
        # Converti HTML in PDF
        html = HTML(string=html_string)
        
        # Crea file temporaneo
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            html.write_pdf(target=tmp.name)
            tmp_file = tmp.name
        
        # Prepara la risposta con il file PDF
        filename = f"municipality_{municipality.name}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        with open(tmp_file, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Elimina il file temporaneo
        os.unlink(tmp_file)
        
        return response