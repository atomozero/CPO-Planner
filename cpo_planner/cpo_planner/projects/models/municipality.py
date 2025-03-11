# cpo_planner/projects/models/municipality.py
from django.db import models
from django.utils.translation import gettext_lazy as _

class Municipality(models.Model):
    """
    Modello per la gestione dei comuni
    """
    name = models.CharField(_('Nome Comune'), max_length=100)
    province = models.CharField(_('Provincia'), max_length=50)
    region = models.CharField(_('Regione'), max_length=50)
    
    def __str__(self):
        return f"{self.name} ({self.province})"
    
    class Meta:
        verbose_name = _('Comune')
        verbose_name_plural = _('Comuni')
        unique_together = ['name', 'province']
