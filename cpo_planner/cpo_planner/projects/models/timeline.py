# cpo_planner/projects/models/timeline.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from datetime import timedelta

class ProjectTimeline(models.Model):
    """
    Modello per la gestione del cronoprogramma del progetto
    """
    project = models.OneToOneField(
        'Project', 
        on_delete=models.CASCADE, 
        related_name='timeline',
        verbose_name=_('Progetto')
    )
    
    # Fasi generali del progetto
    planning_start = models.DateField(_('Inizio Pianificazione'))
    planning_end = models.DateField(_('Fine Pianificazione'))
    
    permitting_start = models.DateField(_('Inizio Richiesta Permessi'))
    permitting_end = models.DateField(_('Fine Richiesta Permessi'))
    
    procurement_start = models.DateField(_('Inizio Approvvigionamento'))
    procurement_end = models.DateField(_('Fine Approvvigionamento'))
    
    installation_start = models.DateField(_('Inizio Installazione'))
    installation_end = models.DateField(_('Fine Installazione'))
    
    testing_start = models.DateField(_('Inizio Test'))
    testing_end = models.DateField(_('Fine Test'))
    
    operation_start = models.DateField(_('Inizio Operatività'))
    
    # Dettagli aggiuntivi
    timeline_notes = models.TextField(_('Note Cronoprogramma'), blank=True, null=True)
    critical_milestones = models.JSONField(_('Milestone Critiche'), default=list)
    
    def is_delayed(self):
        """
        Verifica se il progetto è in ritardo rispetto al cronoprogramma
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        if self.planning_end < today and not self.has_completed_planning():
            return True
        if self.permitting_end < today and not self.has_completed_permitting():
            return True
        if self.procurement_end < today and not self.has_completed_procurement():
            return True
        if self.installation_end < today and not self.has_completed_installation():
            return True
        if self.testing_end < today and not self.has_completed_testing():
            return True
        
        return False
    
    def has_completed_planning(self):
        # Implementa la logica per verificare se la fase di pianificazione è completata
        return True
    
    def has_completed_permitting(self):
        # Implementa la logica per verificare se la fase di permessi è completata
        return True
    
    def has_completed_procurement(self):
        # Implementa la logica per verificare se la fase di approvvigionamento è completata
        return True
    
    def has_completed_installation(self):
        # Implementa la logica per verificare se la fase di installazione è completata
        return True
    
    def has_completed_testing(self):
        # Implementa la logica per verificare se la fase di test è completata
        return True
    
    def get_project_duration(self):
        """
        Calcola la durata totale del progetto in giorni
        """
        return (self.testing_end - self.planning_start).days
    
    def get_current_phase(self):
        """
        Determina la fase corrente del progetto
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        if today < self.planning_end:
            return 'planning'
        elif today < self.permitting_end:
            return 'permitting'
        elif today < self.procurement_end:
            return 'procurement'
        elif today < self.installation_end:
            return 'installation'
        elif today < self.testing_end:
            return 'testing'
        else:
            return 'operation'
    
    def export_to_json(self):
        """
        Esporta il cronoprogramma in formato JSON
        """
        return {
            'planning': {
                'start': self.planning_start.isoformat(),
                'end': self.planning_end.isoformat(),
                'duration': (self.planning_end - self.planning_start).days
            },
            'permitting': {
                'start': self.permitting_start.isoformat(),
                'end': self.permitting_end.isoformat(),
                'duration': (self.permitting_end - self.permitting_start).days
            },
            'procurement': {
                'start': self.procurement_start.isoformat(),
                'end': self.procurement_end.isoformat(),
                'duration': (self.procurement_end - self.procurement_start).days
            },
            'installation': {
                'start': self.installation_start.isoformat(),
                'end': self.installation_end.isoformat(),
                'duration': (self.installation_end - self.installation_start).days
            },
            'testing': {
                'start': self.testing_start.isoformat(),
                'end': self.testing_end.isoformat(),
                'duration': (self.testing_end - self.testing_start).days
            },
            'operation': {
                'start': self.operation_start.isoformat()
            },
            'total_duration': self.get_project_duration(),
            'critical_milestones': self.critical_milestones
        }
    
    def __str__(self):
        return f"Cronoprogramma: {self.project.name}"
    
    class Meta:
        verbose_name = _('Cronoprogramma Progetto')
        verbose_name_plural = _('Cronoprogrammi Progetti')


class StationTimeline(models.Model):
    """
    Modello per la gestione del cronoprogramma di una singola stazione di ricarica
    """
    charging_station = models.OneToOneField(
        'ChargingStation', 
        on_delete=models.CASCADE, 
        related_name='timeline',
        verbose_name=_('Stazione di Ricarica')
    )
    
    # Fasi specifiche della stazione
    design_start = models.DateField(_('Inizio Progettazione'))
    design_end = models.DateField(_('Fine Progettazione'))
    
    permit_application_date = models.DateField(_('Data Richiesta Permessi'))
    permit_approval_date = models.DateField(_('Data Approvazione Permessi'), null=True, blank=True)
    
    equipment_order_date = models.DateField(_('Data Ordine Apparecchiature'))
    equipment_delivery_date = models.DateField(_('Data Consegna Apparecchiature'), null=True, blank=True)
    
    site_preparation_start = models.DateField(_('Inizio Preparazione Sito'))
    site_preparation_end = models.DateField(_('Fine Preparazione Sito'))
    
    installation_start = models.DateField(_('Inizio Installazione'))
    installation_end = models.DateField(_('Fine Installazione'))
    
    grid_connection_date = models.DateField(_('Data Connessione Rete'))
    testing_date = models.DateField(_('Data Test'))
    commissioning_date = models.DateField(_('Data Messa in Servizio'))
    
    # Dettagli aggiuntivi
    status_notes = models.TextField(_('Note Stato'), blank=True, null=True)
    
    def get_installation_duration(self):
        """
        Calcola la durata totale dell'installazione in giorni
        """
        return (self.commissioning_date - self.design_start).days
    
    def get_current_status(self):
        """
        Determina lo stato corrente dell'installazione
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        if today < self.design_end:
            return 'design'
        elif self.permit_approval_date is None or today < self.permit_approval_date:
            return 'permitting'
        elif self.equipment_delivery_date is None or today < self.equipment_delivery_date:
            return 'procurement'
        elif today < self.site_preparation_end:
            return 'site_preparation'
        elif today < self.installation_end:
            return 'installation'
        elif today < self.grid_connection_date:
            return 'grid_connection'
        elif today < self.testing_date:
            return 'testing'
        elif today < self.commissioning_date:
            return 'commissioning'
        else:
            return 'operational'
    
    def is_delayed(self):
        """
        Verifica se l'installazione è in ritardo
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        # Verifico solo le date definitive, non quelle che potrebbero essere ancora da definire
        if self.design_end < today and self.get_current_status() == 'design':
            return True
        if self.site_preparation_end < today and self.get_current_status() == 'site_preparation':
            return True
        if self.installation_end < today and self.get_current_status() == 'installation':
            return True
        
        return False
    
    def __str__(self):
        return f"Timeline: {self.charging_station.name}"
    
    class Meta:
        verbose_name = _('Cronoprogramma Stazione')
        verbose_name_plural = _('Cronoprogrammi Stazioni')