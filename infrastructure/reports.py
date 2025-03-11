# reports.py
from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from django.utils.translation import gettext as _

from .models import Municipality, ChargingProject, ChargingStation

class PDFGenerator:
    """
    Generatore base per i report PDF
    """
    def __init__(self, buffer=None, pagesize=A4):
        self.buffer = buffer if buffer else BytesIO()
        self.pagesize = pagesize
        self.width, self.height = self.pagesize
        self.styles = getSampleStyleSheet()
        
        # Stili personalizzati
        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=12,
        ))
        
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
        ))
    
    def _create_document(self):
        """Crea il documento PDF base"""
        return SimpleDocTemplate(
            self.buffer,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            pagesize=self.pagesize
        )
    
    def generate(self):
        """Da implementare nelle classi figlie"""
        raise NotImplementedError("Questo metodo deve essere implementato dalle classi figlie")
    
    def get_pdf(self):
        """Restituisce il buffer con il PDF generato"""
        self.buffer.seek(0)
        return self.buffer


class MunicipalityReportGenerator(PDFGenerator):
    """Generatore di report per i comuni"""
    
    def __init__(self, municipality, buffer=None, pagesize=A4):
        super().__init__(buffer, pagesize)
        self.municipality = municipality
    
    def generate(self):
        doc = self._create_document()
        story = []
        
        # Titolo del report
        title = Paragraph(f"{self.municipality.name} ({self.municipality.province}) - {_('Report completo')}", self.styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Dettagli del comune
        story.append(Paragraph(_("Dettagli del comune"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        # Tabella dei dettagli
        data = [
            [_("Popolazione"), f"{self.municipality.population:,}" if self.municipality.population else "N/A"],
            [_("Tasso di adozione EV"), f"{self.municipality.ev_adoption_rate}%"],
            [_("Potenziali utenti EV"), f"{self.municipality.potential_ev_users():,}"],
            [_("Numero di progetti"), f"{self.municipality.charging_projects.count()}"],
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 24))
        
        # Lista dei progetti
        story.append(Paragraph(_("Progetti attivi"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        projects = self.municipality.charging_projects.all()
        if projects:
            # Header della tabella
            project_data = [
                [_("Nome progetto"), _("Stato"), _("Budget"), _("Stazioni"), _("Completamento")]
            ]
            
            # Dati dei progetti
            for project in projects:
                project_data.append([
                    project.name,
                    dict(ChargingProject.STATUS_CHOICES)[project.status],
                    f"€ {project.budget:,.2f}",
                    f"{project.charging_stations.count()}",
                    f"{project.completion_percentage()}%"
                ])
            
            project_table = Table(project_data, colWidths=[120, 80, 80, 60, 80])
            project_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            
            story.append(project_table)
        else:
            story.append(Paragraph(_("Nessun progetto disponibile"), self.styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 36))
        story.append(Paragraph(f"{_('Report generato il')}: {date.today().strftime('%d/%m/%Y')}", self.styles['Normal']))
        
        doc.build(story)
        return self.get_pdf()


class ChargingProjectReportGenerator(PDFGenerator):
    """Generatore di report per i progetti di ricarica"""
    
    def __init__(self, project, buffer=None, pagesize=A4):
        super().__init__(buffer, pagesize)
        self.project = project
    
    def generate(self):
        doc = self._create_document()
        story = []
        
        # Titolo del report
        title = Paragraph(f"{self.project.name} - {_('Business Plan')}", self.styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Dettagli del progetto
        story.append(Paragraph(_("Informazioni generali"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        # Tabella dei dettagli
        data = [
            [_("Comune"), f"{self.project.municipality.name} ({self.project.municipality.province})"],
            [_("Stato attuale"), dict(ChargingProject.STATUS_CHOICES)[self.project.status]],
            [_("Data di inizio"), self.project.start_date.strftime('%d/%m/%Y') if self.project.start_date else "N/A"],
            [_("Completamento stimato"), self.project.estimated_completion_date.strftime('%d/%m/%Y') if self.project.estimated_completion_date else "N/A"],
            [_("Budget totale"), f"€ {self.project.budget:,.2f}"],
            [_("Completamento"), f"{self.project.completion_percentage()}%"],
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 24))
        
        # Lista delle stazioni di ricarica
        story.append(Paragraph(_("Stazioni di ricarica"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        stations = self.project.charging_stations.all()
        if stations:
            # Header della tabella
            station_data = [
                [_("Codice"), _("Indirizzo"), _("Tipo"), _("Potenza (kW)"), _("Connettori"), _("Costo totale")]
            ]
            
            # Dati delle stazioni
            total_cost = 0
            for station in stations:
                total_cost += station.total_costs()
                station_data.append([
                    station.code,
                    station.location,
                    dict(ChargingStation.CONNECTION_CHOICES)[station.connection_type],
                    f"{station.max_power}",
                    f"{station.num_connectors}",
                    f"€ {station.total_costs():,.2f}"
                ])
            
            # Riga del totale
            station_data.append([
                _("TOTALE"), "", "", "", "",
                f"€ {total_cost:,.2f}"
            ])
            
            station_table = Table(station_data, colWidths=[60, 120, 60, 60, 60, 80])
            station_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ]))
            
            story.append(station_table)
        else:
            story.append(Paragraph(_("Nessuna stazione di ricarica disponibile"), self.styles['Normal']))
        
        # Footer
        story.append(Spacer(1, 36))
        story.append(Paragraph(f"{_('Business Plan generato il')}: {date.today().strftime('%d/%m/%Y')}", self.styles['Normal']))
        story.append(Paragraph(_("Documento ad uso interno"), self.styles['Normal']))
        
        doc.build(story)
        return self.get_pdf()


class ChargingStationSheetGenerator(PDFGenerator):
    """Generatore di scheda tecnica per le stazioni di ricarica"""
    
    def __init__(self, station, buffer=None, pagesize=A4):
        super().__init__(buffer, pagesize)
        self.station = station
    
    def generate(self):
        doc = self._create_document()
        story = []
        
        # Titolo del report
        title = Paragraph(f"{_('Scheda Tecnica')} - {self.station.code}", self.styles['Title'])
        story.append(title)
        story.append(Spacer(1, 12))
        
        # Informazioni generali
        story.append(Paragraph(_("Informazioni generali"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        # Tabella delle informazioni generali
        data = [
            [_("Codice stazione"), self.station.code],
            [_("Progetto"), self.station.project.name],
            [_("Comune"), f"{self.station.project.municipality.name} ({self.station.project.municipality.province})"],
            [_("Indirizzo"), self.station.location],
            [_("Coordinate"), f"Lat: {self.station.latitude}, Long: {self.station.longitude}" if self.station.latitude and self.station.longitude else "N/A"],
            [_("Stato"), dict(ChargingStation.STATUS_CHOICES)[self.station.status]],
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 24))
        
        # Specifiche tecniche
        story.append(Paragraph(_("Specifiche tecniche"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        tech_data = [
            [_("Tipo di connessione"), dict(ChargingStation.CONNECTION_CHOICES)[self.station.connection_type]],
            [_("Potenza massima"), f"{self.station.max_power} kW"],
            [_("Numero di connettori"), f"{self.station.num_connectors}"],
            [_("Integrazione fotovoltaico"), _("Sì") if self.station.has_pv_system else _("No")],
        ]
        
        if self.station.has_pv_system and self.station.pv_power:
            tech_data.append([_("Potenza fotovoltaico"), f"{self.station.pv_power} kWp"])
        
        tech_table = Table(tech_data, colWidths=[200, 200])
        tech_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(tech_table)
        story.append(Spacer(1, 24))
        
        # Informazioni finanziarie
        story.append(Paragraph(_("Informazioni economiche"), self.styles['Subtitle']))
        story.append(Spacer(1, 6))
        
        fin_data = [
            [_("Costo d'acquisto"), f"€ {self.station.purchase_cost:,.2f}"],
            [_("Costo d'installazione"), f"€ {self.station.installation_cost:,.2f}"],
            [_("Costo di allaccio"), f"€ {self.station.connection_cost:,.2f}"],
            [_("Costo totale"), f"€ {self.station.total_costs():,.2f}"],
        ]
        
        fin_table = Table(fin_data, colWidths=[200, 200])
        fin_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('BACKGROUND', (0, -1), (0, -1), colors.grey),
            ('TEXTCOLOR', (0, -1), (0, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        
        story.append(fin_table)
        
        # Date importanti
        if self.station.installation_date or self.station.active_date:
            story.append(Spacer(1, 24))
            story.append(Paragraph(_("Date importanti"), self.styles['Subtitle']))
            story.append(Spacer(1, 6))
            
            date_data = []
            if self.station.installation_date:
                date_data.append([_("Data di installazione"), self.station.installation_date.strftime('%d/%m/%Y')])
            if self.station.active_date:
                date_data.append([_("Data di attivazione"), self.station.active_date.strftime('%d/%m/%Y')])
            
            if date_data:
                date_table = Table(date_data, colWidths=[200, 200])
                date_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('PADDING', (0, 0), (-1, -1), 6),
                ]))
                story.append(date_table)
        
        # Footer
        story.append(Spacer(1, 36))
        story.append(Paragraph(f"{_('Scheda generata il')}: {date.today().strftime('%d/%m/%Y')}", self.styles['Normal']))
        story.append(Paragraph(_("Documento per uso amministrativo"), self.styles['Normal']))
        
        doc.build(story)
        return self.get_pdf()