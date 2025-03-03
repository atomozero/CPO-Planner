from django.db import models
from django.utils.translation import gettext_lazy as _

class Project(models.Model):
    name = models.CharField(_('Nome'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True)
    start_date = models.DateField(_('Data inizio'))
    end_date = models.DateField(_('Data fine'), null=True, blank=True)
    
    def __str__(self):
        return self.name

class SubProject(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='subprojects')
    name = models.CharField(_('Nome'), max_length=255)
    description = models.TextField(_('Descrizione'), blank=True)
    
    def __str__(self):
        return self.name

class ChargingStation(models.Model):
    subproject = models.ForeignKey(SubProject, on_delete=models.CASCADE, related_name='charging_stations')
    name = models.CharField(_('Nome'), max_length=255)
    location = models.CharField(_('Posizione'), max_length=255)
    
    def __str__(self):
        return self.name