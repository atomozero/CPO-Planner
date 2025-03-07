from django.db import models
from django.utils.translation import gettext_lazy as _

def municipality_logo_path(instance, filename):
    """Path per il logo del comune"""
    return f'municipality_logos/municipality_{instance.id}/{filename}'

class Municipality(models.Model):
    """Comune in cui vengono installate le stazioni di ricarica"""
    name = models.CharField(_("Nome Comune"), max_length=255)
    province = models.CharField(_("Provincia"), max_length=100)
    region = models.CharField(_("Regione"), max_length=100)
    logo = models.ImageField(_("Logo Comune"), upload_to=municipality_logo_path, blank=True, null=True)
    
    # Demografia e dati EV
    population = models.PositiveIntegerField(_("Popolazione"), null=True, blank=True)
    area_sqkm = models.DecimalField(_("Area (km quadri)"), max_digits=10, decimal_places=2, null=True, blank=True)
    ev_adoption_rate = models.FloatField(_("Tasso di adozione EV (%)"), default=2.0)
    
    # Coordinate geografiche
    latitude = models.FloatField(_("Latitudine"), null=True, blank=True)
    longitude = models.FloatField(_("Longitudine"), null=True, blank=True)
    
    # Contatti
    contact_name = models.CharField(_("Nome Contatto"), max_length=255, blank=True)
    contact_email = models.EmailField(_("Email Contatto"), blank=True)
    contact_phone = models.CharField(_("Telefono Contatto"), max_length=20, blank=True)
    notes = models.TextField(_("Note"), blank=True)
    
    def potential_ev_users(self):
        """Calcola potenziali utenti di veicoli elettrici"""
        if self.population:
            return int(self.population * (self.ev_adoption_rate / 100))
        return 0
    
    def __str__(self):
        return f"{self.name} ({self.province})"
    
    class Meta:
        verbose_name = _("Comune")
        verbose_name_plural = _("Comuni")
        unique_together = ['name', 'province']
        ordering = ["name", "province"]