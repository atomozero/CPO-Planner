from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
from django.conf import settings
from decimal import Decimal

class ChargingStation(models.Model):
    """Stazione di ricarica per veicoli elettrici"""
    # Identificazione di base
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subproject = models.ForeignKey('SubProject', on_delete=models.CASCADE, related_name='charging_stations', verbose_name=_('Sotto-Progetto'))
    name = models.CharField(_("Nome Stazione"), max_length=255)
    identifier = models.CharField(_("Identificatore Stazione"), max_length=50, unique=True, default="CS-000000")
    
    # Localizzazione
    address = models.CharField(_("Indirizzo"), max_length=255, default="")
    latitude = models.DecimalField(_("Latitudine"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_("Longitudine"), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Specifiche tecniche
    STATION_TYPES = [
        ('ac_slow', _('AC Lenta (fino a 7.4 kW)')),
        ('ac_fast', _('AC Veloce (11-22 kW)')),
        ('dc_fast', _('DC Veloce (50 kW)')),
        ('hpc', _('High Power Charger (>100 kW)')),
    ]
    station_type = models.CharField(_("Tipo Stazione"), max_length=20, choices=STATION_TYPES)
    
    POWER_TYPE_CHOICES = [
        ('ac', _('AC')),
        ('dc', _('DC')),
        ('ac_dc', _('AC/DC')),
    ]
    power_type = models.CharField(_("Tipo di Potenza"), max_length=10, choices=POWER_TYPE_CHOICES, default='ac')
    power_kw = models.DecimalField(_("Potenza"), max_digits=8, decimal_places=2, help_text='kW', default=22.0)
    connector_types = models.CharField(_("Tipi di Connettori"), max_length=255, help_text=_('Separati da virgola'), default="Type 2")
    num_connectors = models.PositiveIntegerField(_("Numero Connettori"), default=2)
    grid_connection_capacity = models.DecimalField(_("Capacita Connessione Rete"), max_digits=8, decimal_places=2, help_text='kW', default=25.0)
    
    # Costi
    station_cost = models.DecimalField(_("Costo Colonnina"), max_digits=10, decimal_places=2, default=0)
    installation_cost = models.DecimalField(_("Costo Installazione"), max_digits=10, decimal_places=2, default=0)
    connection_cost = models.DecimalField(_("Costo Allaccio"), max_digits=10, decimal_places=2, default=0)
    design_cost = models.DecimalField(_("Costo Progettazione"), max_digits=10, decimal_places=2, default=0)
    permit_cost = models.DecimalField(_("Costo Permessi"), max_digits=10, decimal_places=2, default=0)
    other_costs = models.DecimalField(_("Altri Costi"), max_digits=10, decimal_places=2, default=0)
    
    # Parametri operativi
    energy_cost_kwh = models.DecimalField(_("Costo Energia (EUR/kWh)"), max_digits=6, decimal_places=4, default=0.25)
    charging_price_kwh = models.DecimalField(_("Prezzo Ricarica (EUR/kWh)"), max_digits=6, decimal_places=4, default=0.45)
    estimated_sessions_day = models.DecimalField(_("Sessioni Stimate/Giorno"), max_digits=6, decimal_places=2, default=5.0)
    avg_kwh_session = models.DecimalField(_("Media kWh/Sessione"), max_digits=6, decimal_places=2, default=15.0)
    
    # Date
    installation_date = models.DateField(_("Data Installazione"), null=True, blank=True)
    activation_date = models.DateField(_("Data Attivazione"), null=True, blank=True)
    
    # Stato
    STATUS_CHOICES = [
        ('planned', _('Pianificata')),
        ('permitting', _('In Fase di Autorizzazione')),
        ('ordered', _('Ordinata')),
        ('installing', _('In Installazione')),
        ('installed', _('Installata')),
        ('testing', _('In Test')),
        ('active', _('Attiva')),
        ('operational', _('Operativa')),
        ('maintenance', _('In Manutenzione')),
        ('offline', _('Fuori Servizio')),
        ('inactive', _('Inattiva')),
        ('decommissioned', _('Dismessa')),
    ]
    status = models.CharField(_("Stato Stazione"), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Integrazione fotovoltaico
    has_photovoltaic_system = models.BooleanField(_("Impianto Fotovoltaico"), default=False)
    photovoltaic_capacity = models.DecimalField(_("Capacita Fotovoltaico"), max_digits=8, decimal_places=2, null=True, blank=True, help_text='kWp')
    
    # Metadati
    notes = models.TextField(_("Note"), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def calculate_total_cost(self):
        """Calcola il costo totale della stazione"""
        return (
            self.station_cost + 
            self.installation_cost + 
            self.connection_cost + 
            self.design_cost + 
            self.permit_cost + 
            self.other_costs
        )
    
    def calculate_annual_revenue(self, include_availability=True, include_seasonality=True):
        """
        Calcola ricavi annuali con maggiore precisione.
        
        Parameters:
        -----------
        include_availability : bool
            Se True, considera i giorni di indisponibilità (mercato settimanale, feste locali, giorni di pioggia).
        include_seasonality : bool
            Se True, considera i fattori stagionali nell'utilizzo (estate +20%, inverno -20%).
            
        Returns:
        --------
        Decimal: Ricavo annuale calcolato in euro
        
        Note:
        -----
        Questo metodo standardizza il calcolo dei ricavi in tutta l'applicazione.
        Formula base: prezzo_kwh * kwh_per_sessione * sessioni_giornaliere * giorni_all'anno
        """
        # Parametri base
        daily_sessions = self.estimated_sessions_day
        price_per_kwh = self.charging_price_kwh
        kwh_per_session = self.avg_kwh_session
        
        # Calcolo base
        daily_revenue = price_per_kwh * kwh_per_session * daily_sessions
        annual_revenue = daily_revenue * 365
        
        # Applica fattore disponibilità se richiesto
        if include_availability and hasattr(self, 'subproject') and self.subproject:
            # Usa il metodo calculate_availability_factor che include i giorni di pioggia
            availability_factor = self.subproject.calculate_availability_factor()
            annual_revenue *= Decimal(str(availability_factor))
            
            # Debug info
            unavailable_days = 0
            if self.subproject.weekly_market_day is not None:
                unavailable_days += 52  # 52 settimane
            if self.subproject.local_festival_days:
                unavailable_days += self.subproject.local_festival_days
                
            rainy_days = self.subproject.rainy_days or 0
            
            print(f"DEBUG - Calcolo ricavi: giorni indisponibili={unavailable_days}, "
                f"giorni pioggia={rainy_days}, fattore disponibilità={availability_factor:.4f}, "
                f"ricavi={annual_revenue:.2f}")
        
        # Applica fattori stagionali se richiesto
        if include_seasonality:
            # Resetta il calcolo annuale e somma i valori mensili con stagionalità
            monthly_total = Decimal('0.0')
            for month in range(1, 13):
                # Fattore stagionale per ogni mese
                seasonal_factor = Decimal('1.2') if month in [6, 7, 8, 9] else (Decimal('0.8') if month in [12, 1, 2] else Decimal('1.0'))
                monthly_sessions = daily_sessions * Decimal('30') * seasonal_factor
                monthly_kwh = monthly_sessions * kwh_per_session
                monthly_revenue = monthly_kwh * price_per_kwh
                monthly_total += monthly_revenue
            
            # Sostituisci il calcolo annuale con quello stagionale
            annual_revenue = monthly_total
        
        return annual_revenue
        
    def calculate_annual_metrics(self):
        """Calcola metriche annuali basate sui dati della stazione"""
        # Utilizza il nuovo metodo standardizzato per il calcolo dei ricavi
        annual_revenue = self.calculate_annual_revenue(include_availability=True, include_seasonality=True)
        annual_costs = self.calculate_annual_operational_costs()
        annual_profit = annual_revenue - annual_costs
        return {
            'annual_revenue': annual_revenue,
            'annual_costs': annual_costs,
            'annual_profit': annual_profit
        }
    
    def calculate_annual_operational_costs(self):
        """Calcola i costi operativi annuali stimati"""
        # Costo energia
        daily_energy_cost = self.energy_cost_kwh * self.avg_kwh_session * self.estimated_sessions_day
        annual_energy_cost = daily_energy_cost * 365
        
        # Costo manutenzione (stimato al 5% del costo della stazione)
        annual_maintenance_cost = self.station_cost * Decimal('0.05')
        
        # Costi operativi totali
        return annual_energy_cost + annual_maintenance_cost
    
    def __str__(self):
        return f"{self.name} ({self.identifier})"
    
    class Meta:
        verbose_name = _("Stazione di Ricarica")
        verbose_name_plural = _("Stazioni di Ricarica")


class ChargingStationPhoto(models.Model):
    """Foto associate alla stazione di ricarica"""
    PHASE_CHOICES = [
        ('pre_installation', _('Prima dell\'installazione')),
        ('during_installation', _('Durante l\'installazione')),
        ('post_installation', _('Dopo l\'installazione')),
    ]
    
    charging_station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='photos', null=True, blank=True)
    subproject = models.ForeignKey('SubProject', on_delete=models.CASCADE, related_name='photos', null=True, blank=True)
    photo = models.ImageField(_("Foto"), upload_to='charging_stations/photos/')
    phase = models.CharField(_("Fase"), max_length=20, choices=PHASE_CHOICES)
    title = models.CharField(_("Titolo"), max_length=100)
    description = models.TextField(_("Descrizione"), blank=True)
    date_taken = models.DateField(_("Data Scatto"), null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_station_photos',
        verbose_name=_('Caricata da')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.charging_station:
            return f"{self.get_phase_display()} - {self.charging_station.name}"
        elif self.subproject:
            return f"{self.get_phase_display()} - {self.subproject.name}"
        else:
            return f"{self.get_phase_display()} - {self.title}"
    
    class Meta:
        verbose_name = _("Foto Stazione di Ricarica")
        verbose_name_plural = _("Foto Stazioni di Ricarica")
        ordering = ['-date_taken', '-created_at']


class SolarInstallation(models.Model):
    """Impianto fotovoltaico associato a una stazione di ricarica"""
    charging_station = models.OneToOneField(ChargingStation, on_delete=models.CASCADE, related_name='solar_installation')
    capacity_kw = models.DecimalField(_("Capacita"), max_digits=8, decimal_places=2, help_text="kWp")
    panel_type = models.CharField(_("Tipo Pannelli"), max_length=100)
    num_panels = models.PositiveIntegerField(_("Numero Pannelli"))
    installation_cost = models.DecimalField(_("Costo Installazione"), max_digits=10, decimal_places=2)
    annual_production_kwh = models.DecimalField(_("Produzione Annuale Stimata"), max_digits=10, decimal_places=2, help_text="kWh")
    installation_date = models.DateField(_("Data Installazione"), null=True, blank=True)
    notes = models.TextField(_("Note"), blank=True)
    
    def __str__(self):
        return f"Impianto FV {self.capacity_kw}kWp - {self.charging_station.name}"
    
    class Meta:
        verbose_name = _("Impianto Fotovoltaico")
        verbose_name_plural = _("Impianti Fotovoltaici")