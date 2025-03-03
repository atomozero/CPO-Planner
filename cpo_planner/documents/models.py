# documents/models.py
import os
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# Commenta temporaneamente l'importazione problematica
# from cpo_planner.projects.models import Project, SubProject, ChargingStation

def document_upload_path(instance, filename):
    """Determina il percorso di upload basato sul tipo di documento e l'entità correlata"""
    today = timezone.now().strftime('%Y/%m/%d')
    entity_type = instance.content_type.model
    entity_id = instance.object_id
    return f'documents/{entity_type}/{entity_id}/{today}/{filename}'

class DocumentCategory(models.Model):
    """Categoria di documenti (es. Permessi, Contratti, Specifiche Tecniche)"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    slug = models.SlugField(_('Slug'), max_length=100, unique=True)
    
    class Meta:
        verbose_name = _('Categoria Documento')
        verbose_name_plural = _('Categorie Documenti')
        ordering = ['name']
    
    def __str__(self):
        return self.name

class DocumentStatus(models.TextChoices):
    DRAFT = 'draft', _('Bozza')
    PENDING = 'pending', _('In Attesa di Approvazione')
    APPROVED = 'approved', _('Approvato')
    REJECTED = 'rejected', _('Respinto')
    EXPIRED = 'expired', _('Scaduto')

class Document(models.Model):
    """Modello principale per i documenti"""
    title = models.CharField(_('Titolo'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True)
    file = models.FileField(_('File'), upload_to=document_upload_path)
    category = models.ForeignKey(
        DocumentCategory, 
        on_delete=models.PROTECT, 
        related_name='documents',
        verbose_name=_('Categoria')
    )
    status = models.CharField(
        _('Stato'),
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.DRAFT
    )
    
    # Campi generici per collegare il documento a diversi tipi di entità
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    
    # Metadati
    version = models.CharField(_('Versione'), max_length=50, blank=True)
    issue_date = models.DateField(_('Data di Emissione'), null=True, blank=True)
    expiry_date = models.DateField(_('Data di Scadenza'), null=True, blank=True)
    
    # Tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_documents',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Documento')
        verbose_name_plural = _('Documenti')
        ordering = ['-updated_at']
        
    def __str__(self):
        return self.title
    
    def file_extension(self):
        """Restituisce l'estensione del file"""
        name, extension = os.path.splitext(self.file.name)
        return extension.lower()
    
    def is_image(self):
        """Verifica se il documento è un'immagine"""
        return self.file_extension() in ['.jpg', '.jpeg', '.png', '.gif']
    
    def is_pdf(self):
        """Verifica se il documento è un PDF"""
        return self.file_extension() == '.pdf'
    
    def file_size_mb(self):
        """Restituisce la dimensione del file in MB"""
        if self.file and hasattr(self.file, 'size'):
            return self.file.size / (1024 * 1024)
        return 0
    
    def is_expired(self):
        """Verifica se il documento è scaduto"""
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False
    
    def save(self, *args, **kwargs):
        # Se il documento è scaduto, aggiorna automaticamente lo stato
        if self.is_expired() and self.status != DocumentStatus.EXPIRED:
            self.status = DocumentStatus.EXPIRED
            
        super().save(*args, **kwargs)

class DocumentNote(models.Model):
    """Note e commenti relativi ai documenti"""
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name=_('Documento')
    )
    text = models.TextField(_('Testo'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='document_notes',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Nota Documento')
        verbose_name_plural = _('Note Documento')
        ordering = ['-created_at']
        
    def __str__(self):
        return f'Nota su {self.document.title} - {self.created_at.strftime("%d/%m/%Y %H:%M")}'

class DocumentTaskStatus(models.TextChoices):
    PENDING = 'pending', _('In attesa')
    IN_PROGRESS = 'in_progress', _('In lavorazione')
    COMPLETED = 'completed', _('Completato')
    CANCELLED = 'cancelled', _('Annullato')

class DocumentTask(models.Model):
    """Attività legate ai documenti (es. ottenere firme, invio permessi)"""
    document = models.ForeignKey(
        Document, 
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('Documento')
    )
    title = models.CharField(_('Titolo'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True)
    status = models.CharField(
        _('Stato'),
        max_length=20,
        choices=DocumentTaskStatus.choices,
        default=DocumentTaskStatus.PENDING
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_document_tasks',
        verbose_name=_('Assegnato a')
    )
    due_date = models.DateField(_('Scadenza'), null=True, blank=True)
    completed_at = models.DateTimeField(_('Completato il'), null=True, blank=True)
    
    # Tracciamento
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_document_tasks',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Attività Documento')
        verbose_name_plural = _('Attività Documenti')
        ordering = ['due_date', '-updated_at']
        
    def __str__(self):
        return self.title
    
    def is_overdue(self):
        """Verifica se l'attività è in ritardo"""
        if self.due_date and self.status != DocumentTaskStatus.COMPLETED:
            return self.due_date < timezone.now().date()
        return False
    
    def save(self, *args, **kwargs):
        # Se l'attività viene completata, registra la data di completamento
        if self.status == DocumentTaskStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)

# Segnali per automatizzare funzioni come:
# - Notifiche per documenti in scadenza
# - Aggiornamenti di stato automatici
# - Integrazione con il sistema di notifica

class ProjectDocument(models.Model):
    """Documento specifico per i progetti"""
    # Commenta temporaneamente il ForeignKey problematico
    # project = models.ForeignKey('cpo_planner.projects.Project', on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(_('Titolo'), max_length=255)
    file = models.FileField(_('File'), upload_to='project_documents/')
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    def __str__(self):
        return self.title
        
    class Meta:
        verbose_name = _('Documento Progetto')
        verbose_name_plural = _('Documenti Progetto')

class DocumentTemplate(models.Model):
    """Template per la generazione automatica di documenti"""
    name = models.CharField(_('Nome'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True)
    file = models.FileField(_('File Template'), upload_to='document_templates/')
    
    # Tipo di documento che può essere generato da questo template
    document_type = models.CharField(_('Tipo Documento'), max_length=100)
    
    # Metadati
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_templates',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    # Stato attivo/inattivo
    is_active = models.BooleanField(_('Attivo'), default=True)
    
    class Meta:
        verbose_name = _('Template Documento')
        verbose_name_plural = _('Template Documenti')
        ordering = ['name']
        
    def __str__(self):
        return self.name