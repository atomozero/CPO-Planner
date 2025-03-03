# mapping/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from cpo_planner.projects.models import ChargingStation, Municipality, Project

User = get_user_model()

class MapSettings(models.Model):
    """Impostazioni della mappa"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    
    # Impostazioni della mappa
    default_center_lat = models.FloatField(
        _('Latitudine Centro'),
        default=41.9028,  # Roma
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    default_center_lng = models.FloatField(
        _('Longitudine Centro'),
        default=12.4964,  # Roma
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    default_zoom = models.IntegerField(
        _('Zoom Predefinito'),
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(18)]
    )
    
    # Stile della mappa
    map_style = models.CharField(
        _('Stile Mappa'),
        max_length=50,
        choices=[
            ('streets', _('Strade')),
            ('outdoors', _('Esterni')),
            ('light', _('Chiaro')),
            ('dark', _('Scuro')),
            ('satellite', _('Satellite')),
            ('satellite-streets', _('Satellite con Strade')),
        ],
        default='streets'
    )
    
    # Opzioni di visualizzazione
    show_clusters = models.BooleanField(
        _('Mostra Cluster'),
        default=True,
        help_text=_('Raggruppa stazioni vicine in cluster')
    )
    
    min_cluster_size = models.IntegerField(
        _('Dimensione Minima Cluster'),
        default=3,
        validators=[MinValueValidator(2), MaxValueValidator(10)],
        help_text=_('Numero minimo di stazioni per formare un cluster')
    )
    
    # Filtri predefiniti
    show_planned = models.BooleanField(
        _('Mostra Stazioni Pianificate'),
        default=True
    )
    
    show_under_construction = models.BooleanField(
        _('Mostra Stazioni in Costruzione'),
        default=True
    )
    
    show_operational = models.BooleanField(
        _('Mostra Stazioni Operative'),
        default=True
    )
    
    # Filtri per potenza
    min_power = models.FloatField(
        _('Potenza Minima (kW)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    max_power = models.FloatField(
        _('Potenza Massima (kW)'),
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Metadati e tracking
    is_default = models.BooleanField(_('Impostazioni Predefinite'), default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_map_settings',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Impostazioni Mappa')
        verbose_name_plural = _('Impostazioni Mappa')
        ordering = ['-is_default', '-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['is_default'],
                condition=models.Q(is_default=True),
                name='unique_default_map_settings'
            )
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Se queste impostazioni sono predefinite, rimuovi il flag dalle altre
        if self.is_default:
            MapSettings.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
            
        super().save(*args, **kwargs)
        
    @classmethod
    def get_default(cls):
        """Ottiene le impostazioni predefinite o crea nuove impostazioni predefinite"""
        try:
            return cls.objects.get(is_default=True)
        except cls.DoesNotExist:
            # Crea impostazioni predefinite con l'utente admin
            try:
                admin = User.objects.filter(is_superuser=True).first()
                if admin:
                    return cls.objects.create(
                        name=_('Impostazioni Predefinite'),
                        is_default=True,
                        created_by=admin
                    )
            except:
                pass
        return None

class CustomMarker(models.Model):
    """Marker personalizzati per la mappa"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    
    # Posizione
    latitude = models.FloatField(
        _('Latitudine'),
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.FloatField(
        _('Longitudine'),
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    
    # Stile del marker
    color = models.CharField(
        _('Colore'),
        max_length=20,
        default='#FF0000'  # Rosso
    )
    
    icon = models.CharField(
        _('Icona'),
        max_length=50,
        choices=[
            ('marker', _('Marker Standard')),
            ('charging-station', _('Stazione di Ricarica')),
            ('car', _('Auto')),
            ('building', _('Edificio')),
            ('info', _('Informazioni')),
            ('warning', _('Avviso')),
            ('star', _('Stella')),
            ('flag', _('Bandiera')),
        ],
        default='marker'
    )
    
    # Impostazioni di visibilità
    is_visible = models.BooleanField(_('Visibile'), default=True)
    
    # Contenuto del popup
    popup_title = models.CharField(_('Titolo Popup'), max_length=255, blank=True)
    popup_content = models.TextField(_('Contenuto Popup'), blank=True)
    
    # Collegamento a progetto/sotto-progetto (opzionale)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='custom_markers',
        verbose_name=_('Progetto'),
        null=True,
        blank=True
    )
    
    municipality = models.ForeignKey(
        Municipality,
        on_delete=models.CASCADE,
        related_name='custom_markers',
        verbose_name=_('Sotto-progetto'),
        null=True,
        blank=True
    )
    
    # Metadati e tracking
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_markers',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Marker Personalizzato')
        verbose_name_plural = _('Marker Personalizzati')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class SavedMap(models.Model):
    """Mappe salvate dagli utenti"""
    name = models.CharField(_('Nome'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    
    # Impostazioni della visualizzazione
    center_lat = models.FloatField(
        _('Latitudine Centro'),
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    center_lng = models.FloatField(
        _('Longitudine Centro'),
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    zoom = models.IntegerField(
        _('Livello Zoom'),
        validators=[MinValueValidator(1), MaxValueValidator(18)]
    )
    
    # Filtri applicati (salvati come JSON)
    filters = models.JSONField(_('Filtri'), default=dict)
    
    # Marker personalizzati inclusi
    custom_markers = models.ManyToManyField(
        CustomMarker,
        related_name='saved_maps',
        verbose_name=_('Marker Personalizzati'),
        blank=True
    )
    
    # Stazioni visualizzate
    charging_stations = models.ManyToManyField(
        ChargingStation,
        related_name='saved_maps',
        verbose_name=_('Stazioni di Ricarica'),
        blank=True
    )
    
    # Progetti visualizzati
    projects = models.ManyToManyField(
        Project,
        related_name='saved_maps',
        verbose_name=_('Progetti'),
        blank=True
    )
    
    # Sotto-progetti visualizzati
    subprojects = models.ManyToManyField(
        Municipality,
        related_name='saved_maps',
        verbose_name=_('Sotto-progetti'),
        blank=True
    )
    
    # Metadati e tracking
    is_public = models.BooleanField(
        _('Pubblico'),
        default=False,
        help_text=_('Se abilitato, la mappa sarà visibile a tutti gli utenti')
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_maps',
        verbose_name=_('Creato da')
    )
    created_at = models.DateTimeField(_('Data Creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultimo Aggiornamento'), auto_now=True)
    
    class Meta:
        verbose_name = _('Mappa Salvata')
        verbose_name_plural = _('Mappe Salvate')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
