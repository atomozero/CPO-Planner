# reporting/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
#from cpo_planner.projects.models import Project, SubProject, ChargingStation

class ReportType(models.TextChoices):
    BUSINESS_PLAN = 'business_plan', _('Business Plan')
    FINANCIAL_REPORT = 'financial_report', _('Report Finanziario')
    PROJECT_OVERVIEW = 'project_overview', _('Panoramica Progetto')
    MUNICIPAL_APPROVAL = 'municipal_approval', _('Documentazione Comune')
    CHARGING_STATION_SPECS = 'charging_station_specs', _('Specifiche Stazione')
    CUSTOM = 'custom', _('Personalizzato')

class ReportTemplate(models.Model):
    """Modello per i template di report"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    type = models.CharField(
        _('Tipo Report'),
        max_length=30,
        choices=ReportType.choices,
        default=ReportType.BUSINESS_PLAN
    )
    template_file = models.FileField(
        _('File Template'),
        upload_to='report_templates/',
        help_text=_('File HTML o template LaTeX')
    )
    is_default = models.BooleanField(_('Default per il tipo'), default=False)
    
    # CSS aggiuntivo per template HTML
    css = models.TextField(_('CSS Aggiuntivo'), blank=True)
    
    # Metadata e tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_report_templates',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Template Report')
        verbose_name_plural = _('Template Report')
        ordering = ['type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['type', 'is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_template_per_type'
            )
        ]
        
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"
    
    def save(self, *args, **kwargs):
        # Se questo template è impostato come default, rimuovi il flag dagli altri
        if self.is_default:
            ReportTemplate.objects.filter(
                type=self.type, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
            
        super().save(*args, **kwargs)

class TemplatePlaceholder(models.Model):
    """Segnaposti disponibili nei template di report"""
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='placeholders',
        verbose_name=_('Template')
    )
    name = models.CharField(_('Nome Segnaposto'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    default_value = models.TextField(_('Valore Predefinito'), blank=True)
    
    class Meta:
        verbose_name = _('Segnaposto Template')
        verbose_name_plural = _('Segnaposti Template')
        ordering = ['template', 'name']
        unique_together = ['template', 'name']
        
    def __str__(self):
        return f"{self.name} ({self.template.name})"

class Report(models.Model):
    """Report generato"""
    title = models.CharField(_('Titolo'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True)
    template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.PROTECT,
        related_name='reports',
        verbose_name=_('Template')
    )
    
    # Entità collegata (opzionale)
    content_type = models.ForeignKey(
        'contenttypes.ContentType', 
        on_delete=models.SET_NULL,
        null=True, 
        blank=True,
        verbose_name=_('Tipo Entità')
    )
    object_id = models.PositiveIntegerField(
        _('ID Oggetto'), 
        null=True, 
        blank=True
    )
    
    # File generato
    generated_file = models.FileField(
        _('File Generato'),
        upload_to='reports/',
        null=True,
        blank=True
    )
    
    # Metadati e tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_reports',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    
    # Flag per il tracciamento
    is_generating = models.BooleanField(_('In Generazione'), default=False)
    generation_started_at = models.DateTimeField(_('Inizio Generazione'), null=True, blank=True)
    generation_completed_at = models.DateTimeField(_('Completamento Generazione'), null=True, blank=True)
    generation_error = models.TextField(_('Errore Generazione'), blank=True)
    
    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Report')
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
    
    @property
    def entity_name(self):
        """Restituisce il nome dell'entità collegata"""
        if self.content_type and self.object_id:
            try:
                return str(self.content_type.get_object_for_this_type(id=self.object_id))
            except:
                return _("Entità non trovata")
        return ""
    
    @property
    def status(self):
        """Restituisce lo stato attuale del report"""
        if self.generation_error:
            return _("Errore")
        elif self.generated_file:
            return _("Completato")
        elif self.is_generating:
            return _("In Generazione")
        else:
            return _("In Attesa")
    
    @property
    def file_url(self):
        """Restituisce l'URL del file generato"""
        if self.generated_file:
            return self.generated_file.url
        return None
    
    def mark_as_generating(self):
        """Segna il report come in fase di generazione"""
        self.is_generating = True
        self.generation_started_at = timezone.now()
        self.generation_error = ""
        self.save(update_fields=['is_generating', 'generation_started_at', 'generation_error'])
    
    def mark_as_completed(self, file_path=None):
        """Segna il report come completato"""
        self.is_generating = False
        self.generation_completed_at = timezone.now()
        if file_path:
            self.generated_file = file_path
        self.save(update_fields=['is_generating', 'generation_completed_at', 'generated_file'])
    
    def mark_as_failed(self, error_message):
        """Segna il report come fallito"""
        self.is_generating = False
        self.generation_error = error_message
        self.save(update_fields=['is_generating', 'generation_error'])

class ReportPlaceholderValue(models.Model):
    """Valori personalizzati per i segnaposti nei report"""
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='placeholder_values',
        verbose_name=_('Report')
    )
    placeholder = models.ForeignKey(
        TemplatePlaceholder,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name=_('Segnaposto')
    )
    value = models.TextField(_('Valore'), blank=True)
    
    class Meta:
        verbose_name = _('Valore Segnaposto Report')
        verbose_name_plural = _('Valori Segnaposti Report')
        unique_together = ['report', 'placeholder']
        
    def __str__(self):
        return f"{self.placeholder.name} per {self.report.title}"