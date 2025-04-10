# cpo_planner/projects/models/document.py
from django.db import models
from django.utils.translation import gettext_lazy as _
import os

def project_document_path(instance, filename):
    """
    Percorso per il salvataggio dei documenti di progetto
    """
    # File saved to MEDIA_ROOT/project_documents/project_<id>/<filename>
    return f'project_documents/project_{instance.project.id}/{filename}'

def station_document_path(instance, filename):
    """
    Percorso per il salvataggio dei documenti della stazione
    """
    # File saved to MEDIA_ROOT/station_documents/station_<id>/<filename>
    return f'station_documents/station_{instance.charging_station.id}/{filename}'

class ProjectDocument(models.Model):
    """
    Modello per la gestione dei documenti associati ai progetti
    """
    project = models.ForeignKey(
        'Project', 
        on_delete=models.CASCADE, 
        related_name='proj_documents',
        verbose_name=_('Progetto')
    )
    
    title = models.CharField(_('Titolo'), max_length=200)
    description = models.TextField(_('Descrizione'), blank=True, null=True)
    
    DOCUMENT_TYPE_CHOICES = [
        ('business_plan', _('Business Plan')),
        ('financial_analysis', _('Analisi Finanziaria')),
        ('project_timeline', _('Cronoprogramma')),
        ('contract', _('Contratto')),
        ('permit', _('Permesso')),
        ('technical_specs', _('Specifiche Tecniche')),
        ('environmental_impact', _('Impatto Ambientale')),
        ('municipality_docs', _('Documentazione Comune')),
        ('other', _('Altro')),
    ]
    document_type = models.CharField(_('Tipo Documento'), max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    
    file = models.FileField(_('File'), upload_to=project_document_path)
    
    created_at = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Data aggiornamento'), auto_now=True)
    
    def get_file_extension(self):
        """
        Restituisce l'estensione del file
        """
        name, extension = os.path.splitext(self.file.name)
        return extension.lstrip('.')
    
    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
    
    class Meta:
        verbose_name = _('Documento Progetto')
        verbose_name_plural = _('Documenti Progetto')


class StationDocument(models.Model):
    """
    Modello per la gestione dei documenti associati alle stazioni di ricarica
    """
    charging_station = models.ForeignKey(
        'ChargingStation', 
        on_delete=models.CASCADE, 
        related_name='documents',
        verbose_name=_('Stazione di Ricarica')
    )
    
    title = models.CharField(_('Titolo'), max_length=200)
    description = models.TextField(_('Descrizione'), blank=True, null=True)
    
    DOCUMENT_TYPE_CHOICES = [
        ('technical_specs', _('Specifiche Tecniche')),
        ('installation_manual', _('Manuale Installazione')),
        ('maintenance_manual', _('Manuale Manutenzione')),
        ('wiring_diagram', _('Schema Elettrico')),
        ('site_plan', _('Planimetria')),
        ('permit', _('Permesso')),
        ('inspection_report', _('Rapporto Ispezione')),
        ('test_report', _('Rapporto Test')),
        ('warranty', _('Garanzia')),
        ('other', _('Altro')),
    ]
    document_type = models.CharField(_('Tipo Documento'), max_length=30, choices=DOCUMENT_TYPE_CHOICES)
    
    file = models.FileField(_('File'), upload_to=station_document_path)
    
    created_at = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Data aggiornamento'), auto_now=True)
    
    def get_file_extension(self):
        """
        Restituisce l'estensione del file
        """
        name, extension = os.path.splitext(self.file.name)
        return extension.lstrip('.')
    
    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()})"
    
    class Meta:
        verbose_name = _('Documento Stazione')
        verbose_name_plural = _('Documenti Stazione')