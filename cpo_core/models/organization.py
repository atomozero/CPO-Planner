from django.db import models
from django.utils.translation import gettext_lazy as _

class Organization(models.Model):
    """Organizzazione che gestisce i progetti di ricarica"""
    name = models.CharField(_("Nome"), max_length=255)
    tax_id = models.CharField(_("Codice Fiscale/P.IVA"), max_length=50, unique=True)
    address = models.TextField(_("Indirizzo"))
    contact_email = models.EmailField(_("Email di contatto"))
    contact_phone = models.CharField(_("Telefono di contatto"), max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Organizzazione")
        verbose_name_plural = _("Organizzazioni")

    def __str__(self):
        return self.name