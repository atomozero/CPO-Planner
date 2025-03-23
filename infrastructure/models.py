from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from decimal import Decimal
from cpo_core.models.municipality import Municipality

class GlobalSettings(models.Model):
    """Impostazioni globali dell'applicazione"""
    # Identificazione
    name = models.CharField(_("Nome configurazione"), max_length=100, default="Default")
    is_active = models.BooleanField(_("Configurazione attiva"), default=True)
    
    # Costi connettività
    sim_data_cost_monthly = models.DecimalField(_("Costo mensile SIM dati (€)"), max_digits=6, decimal_places=2, default=10.0)
    modem_4g_cost = models.DecimalField(_("Costo modem 4G (€)"), max_digits=8, decimal_places=2, default=150.0)
    
    # Costi energetici
    default_energy_cost = models.DecimalField(_("Costo energia predefinito (€/kWh)"), max_digits=6, decimal_places=4, default=0.25)
    default_energy_price = models.DecimalField(_("Prezzo ricarica predefinito (€/kWh)"), max_digits=6, decimal_places=4, default=0.45)
    
    # Costi assicurativi
    insurance_cost_per_station = models.DecimalField(_("Costo assicurazione per stazione (€/anno)"), max_digits=8, decimal_places=2, default=200.0)
    
    # Costi manutenzione
    maintenance_cost_percentage = models.DecimalField(_("Percentuale costo manutenzione annuale"), max_digits=5, decimal_places=2, default=5.0, 
        help_text=_("Percentuale del costo di acquisto per la manutenzione annuale"))
    
    # Tasse occupazione suolo
    public_land_fee_per_sqm = models.DecimalField(_("Tassa occupazione suolo pubblico (€/mq/anno)"), max_digits=8, decimal_places=2, default=50.0)
    
    # Parametri economici
    vat_percentage = models.DecimalField(_("Percentuale IVA"), max_digits=5, decimal_places=2, default=22.0)
    inflation_rate = models.DecimalField(_("Tasso d'inflazione annuale (%)"), max_digits=5, decimal_places=2, default=2.0)
    
    # Date e metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Impostazioni Globali")
        verbose_name_plural = _("Impostazioni Globali")
    
    def __str__(self):
        return f"{self.name} ({self.updated_at.strftime('%d/%m/%Y')})"
    
    def save(self, *args, **kwargs):
        """Assicura che ci sia sempre solo una configurazione attiva"""
        if self.is_active:
            # Disattiva tutte le altre configurazioni
            GlobalSettings.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_active(cls):
        """Ottiene la configurazione attiva, o ne crea una nuova se non esiste"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            # Se non esiste una configurazione attiva, crea quella predefinita
            settings = cls(name="Default", is_active=True)
            settings.save()
            return settings

class Municipality(models.Model):
    name = models.CharField(_("Nome Comune"), max_length=100)
    province = models.CharField(_("Provincia"), max_length=100)
    region = models.CharField(_("Regione"), max_length=100, blank=True)
    population = models.IntegerField(_("Popolazione"), blank=True, null=True)
    ev_adoption_rate = models.FloatField(_("Tasso di adozione EV (%)"), default=2.0)
    logo = models.ImageField(_("Logo Comune"), upload_to="municipality_logos", blank=True, null=True)
    
    class Meta:
        verbose_name = _("Comune")
        verbose_name_plural = _("Comuni")
        ordering = ["name", "province"]
    
    def __str__(self):
        return f"{self.name} ({self.province})"
    
    def potential_ev_users(self):
        """Calcola potenziali utenti di veicoli elettrici"""
        if self.population:
            return int(self.population * (self.ev_adoption_rate / 100))
        return 0


class ChargingProject(models.Model):
    name = models.CharField(_("Nome Progetto"), max_length=200)
    municipality = models.ForeignKey(
        Municipality, 
        on_delete=models.CASCADE,
        related_name="charging_projects",
        verbose_name=_("Comune")
    )
    start_date = models.DateField(_("Data di inizio"), blank=True, null=True)
    estimated_completion_date = models.DateField(_("Data di completamento stimata"), blank=True, null=True)
    actual_completion_date = models.DateField(_("Data di completamento effettiva"), blank=True, null=True)
    budget = models.DecimalField(_("Budget totale (€)"), max_digits=10, decimal_places=2, default=0)
    
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('approval', _('Approvazione')),
        ('installation', _('Installazione')),
        ('testing', _('Collaudo')),
        ('operational', _('Operativo')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='planning')
    
    class Meta:
        verbose_name = _("Progetto di ricarica")
        verbose_name_plural = _("Progetti di ricarica")
        ordering = ["municipality", "name"]
    
    def __str__(self):
        return f"{self.name} - {self.municipality}"
    
    def completion_percentage(self):
        """Calcola la percentuale di completamento del progetto"""
        # Logica da implementare basata sullo stato e sul numero di stazioni completate
        if self.status == 'operational':
            return 100
        elif self.status == 'testing':
            return 90
        elif self.status == 'installation':
            return 60
        elif self.status == 'approval':
            return 30
        else:
            return 10
            
    def get_status_display(self):
        """Ritorna il display value dello stato"""
        for code, display in self.STATUS_CHOICES:
            if code == self.status:
                return display
        return ""
        
    def get_status_color(self):
        """Ritorna il colore associato allo stato per uso nei templates"""
        if self.status == 'operational':
            return 'success'
        elif self.status == 'testing':
            return 'info'
        elif self.status == 'installation':
            return 'primary'
        elif self.status == 'approval':
            return 'warning'
        else:
            return 'secondary'


class ChargingStation(models.Model):
    project = models.ForeignKey(
        ChargingProject, 
        on_delete=models.CASCADE,
        related_name="charging_stations",
        verbose_name=_("Progetto")
    )
    code = models.CharField(_("Codice identificativo"), max_length=50)
    location = models.CharField(_("Indirizzo"), max_length=255)
    latitude = models.FloatField(_("Latitudine"), blank=True, null=True)
    longitude = models.FloatField(_("Longitudine"), blank=True, null=True)
    
    # Dati tecnici
    CONNECTION_CHOICES = [
        ('ac', _('AC - Corrente Alternata')),
        ('dc', _('DC - Corrente Continua')),
        ('hybrid', _('Ibrido AC/DC')),
    ]
    connection_type = models.CharField(_("Tipo di connessione"), max_length=10, choices=CONNECTION_CHOICES)
    
    max_power = models.FloatField(_("Potenza massima (kW)"))
    num_connectors = models.IntegerField(_("Numero di connettori"), default=2)
    
    # Costi
    purchase_cost = models.DecimalField(_("Costo d'acquisto (€)"), max_digits=10, decimal_places=2)
    installation_cost = models.DecimalField(_("Costo d'installazione (€)"), max_digits=10, decimal_places=2)
    connection_cost = models.DecimalField(_("Costo di allaccio (€)"), max_digits=10, decimal_places=2)
    
    # Costi aggiuntivi per connettività
    modem_4g_cost = models.DecimalField(_("Costo modem 4G (€)"), max_digits=8, decimal_places=2, default=0, help_text=_("Costo aggiuntivo per il modem 4G se richiesto"))
    sim_annual_cost = models.DecimalField(_("Costo annuale SIM dati (€)"), max_digits=8, decimal_places=2, default=0, help_text=_("Costo annuale per la SIM dati se richiesta"))
    
    # Specifiche tecniche
    ground_area = models.DecimalField(_("Superficie occupata (mq)"), max_digits=6, decimal_places=2, blank=True, null=True, help_text=_("Area occupata sul terreno in mq, utile per il calcolo della tassa di occupazione"))
    
    # Stati e date
    installation_date = models.DateField(_("Data di installazione"), blank=True, null=True)
    active_date = models.DateField(_("Data di attivazione"), blank=True, null=True)
    
    STATUS_CHOICES = [
        ('planned', _('Pianificata')),
        ('ordered', _('Ordinata')),
        ('installed', _('Installata')),
        ('active', _('Attiva')),
        ('maintenance', _('In manutenzione')),
        ('disabled', _('Disattivata')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Integrazione con fotovoltaico
    has_pv_system = models.BooleanField(_("Integrazione fotovoltaico"), default=False)
    pv_power = models.FloatField(_("Potenza fotovoltaico (kWp)"), blank=True, null=True)
    
    class Meta:
        verbose_name = _("Stazione di ricarica")
        verbose_name_plural = _("Stazioni di ricarica")
        ordering = ["project", "code"]
        
    def __str__(self):
        return f"{self.code} - {self.location}"
    
    def total_costs(self):
        """Calcola il costo totale della stazione"""
        total = self.purchase_cost + self.installation_cost + self.connection_cost
        if self.has_pv_system and self.has_4g:
            total += self.modem_4g_cost
        return total
    
    def annual_costs(self):
        """Calcola i costi annuali di gestione"""
        annual = Decimal('0.0')
        # Aggiungi costo SIM se ha connessione 4G
        if hasattr(self, 'has_4g') and self.has_4g:
            annual += self.sim_annual_cost
        return annual
        
    def get_status_display(self):
        """Ritorna il display value dello stato"""
        for code, display in self.STATUS_CHOICES:
            if code == self.status:
                return display
        return ""
        
    def get_status_color(self):
        """Ritorna il colore associato allo stato per uso nei templates"""
        if self.status == 'active':
            return 'success'
        elif self.status == 'installed':
            return 'info'
        elif self.status == 'ordered':
            return 'primary'
        elif self.status == 'planned':
            return 'secondary'
        elif self.status == 'maintenance':
            return 'warning'
        else:  # disabled
            return 'danger'

# models.py (aggiungi questa classe)
class PunData(models.Model):
    """Dati del Prezzo Unico Nazionale (PUN) italiano per l'energia elettrica"""
    date = models.DateField(_("Data"))
    hour = models.IntegerField(_("Ora"), choices=[(i, f"{i:02d}:00") for i in range(24)])
    price = models.DecimalField(_("Prezzo (€/MWh)"), max_digits=8, decimal_places=4)
    zone = models.CharField(_("Zona di mercato"), max_length=10, default="NORD")
    
    # Fasce orarie
    TIMEBAND_CHOICES = [
        ('F1', _('F1 - Ore di punta')),
        ('F2', _('F2 - Ore intermedie')),
        ('F3', _('F3 - Ore fuori punta')),
    ]
    timeband = models.CharField(_("Fascia oraria"), max_length=2, choices=TIMEBAND_CHOICES)
    
    class Meta:
        verbose_name = _("Dato PUN")
        verbose_name_plural = _("Dati PUN")
        ordering = ["-date", "hour"]
        unique_together = ('date', 'hour', 'zone')
        
    def __str__(self):
        return f"PUN {self.date} {self.hour}:00 - {self.price} €/MWh"
    
    @staticmethod
    def get_timeband(date, hour):
        """Determina la fascia oraria F1, F2 o F3 in base a data e ora"""
        import datetime
        weekday = date.weekday()  # 0=lunedì, 6=domenica
        
        # F3: domeniche e festivi (tutto il giorno)
        if weekday == 6:
            return 'F3'
            
        # F1: lunedì-venerdì 8:00-19:00 (esclusi festivi)
        if 0 <= weekday <= 4 and 8 <= hour < 19:
            return 'F1'
            
        # F2: lunedì-venerdì 7:00-8:00 e 19:00-23:00, sabato 7:00-23:00
        if (0 <= weekday <= 4 and (7 == hour or 19 <= hour < 23)) or \
           (weekday == 5 and 7 <= hour < 23):
            return 'F2'
            
        # F3: tutto il resto (lunedì-sabato 23:00-7:00)
        return 'F3'

class EnergyPriceProjection(models.Model):
    """Proiezioni di prezzi energetici basate su dati PUN storici e inflazione"""
    created_at = models.DateTimeField(_("Data creazione"), auto_now_add=True)
    year = models.IntegerField(_("Anno di riferimento"))
    month = models.IntegerField(_("Mese di riferimento"), choices=[(i, i) for i in range(1, 13)])
    
    # Prezzi medi proiettati per fascia
    f1_price = models.DecimalField(_("Prezzo medio F1 (€/kWh)"), max_digits=6, decimal_places=4)
    f2_price = models.DecimalField(_("Prezzo medio F2 (€/kWh)"), max_digits=6, decimal_places=4)
    f3_price = models.DecimalField(_("Prezzo medio F3 (€/kWh)"), max_digits=6, decimal_places=4)
    
    # Prezzo medio proiettato generale
    avg_price = models.DecimalField(_("Prezzo medio (€/kWh)"), max_digits=6, decimal_places=4)
    
    # Parametri usati per la proiezione
    inflation_rate = models.DecimalField(_("Tasso inflazione applicato (%)"), max_digits=5, decimal_places=2)
    base_period_start = models.DateField(_("Inizio periodo base"))
    base_period_end = models.DateField(_("Fine periodo base"))
    
    notes = models.TextField(_("Note"), blank=True)
    
    class Meta:
        verbose_name = _("Proiezione prezzi energia")
        verbose_name_plural = _("Proiezioni prezzi energia")
        ordering = ["-year", "-month"]
        unique_together = ('year', 'month')
        
    def __str__(self):
        return f"Proiezione {self.month}/{self.year}: media {self.avg_price} €/kWh"

class ElectricityTariff(models.Model):
    name = models.CharField(_("Nome tariffa"), max_length=100)
    provider = models.CharField(_("Fornitore"), max_length=100)
    active = models.BooleanField(_("Attiva"), default=True)
    
    # Tipo di tariffa
    TARIFF_TYPE_CHOICES = [
        ('fixed', _('Prezzo Fisso')),
        ('pun', _('Indicizzato PUN')),
    ]
    tariff_type = models.CharField(_("Tipo di tariffa"), max_length=10, choices=TARIFF_TYPE_CHOICES, default='fixed')
    
    # Costi energia per fasce di potenza (per tariffe a prezzo fisso)
    cost_tier1 = models.DecimalField(_("Costo €/kWh (≤ 7kW)"), max_digits=6, decimal_places=4, default=0.25, 
                                   help_text=_("Solo per tariffe a prezzo fisso"))
    cost_tier2 = models.DecimalField(_("Costo €/kWh (≤ 22kW)"), max_digits=6, decimal_places=4, default=0.30,
                                   help_text=_("Solo per tariffe a prezzo fisso"))
    cost_tier3 = models.DecimalField(_("Costo €/kWh (≤ 50kW)"), max_digits=6, decimal_places=4, default=0.35,
                                   help_text=_("Solo per tariffe a prezzo fisso"))
    cost_tier4 = models.DecimalField(_("Costo €/kWh (≤ 150kW)"), max_digits=6, decimal_places=4, default=0.40,
                                   help_text=_("Solo per tariffe a prezzo fisso"))
    cost_tier5 = models.DecimalField(_("Costo €/kWh (> 150kW)"), max_digits=6, decimal_places=4, default=0.45,
                                   help_text=_("Solo per tariffe a prezzo fisso"))
    
    # Componenti per tariffa indicizzata PUN
    pun_fee_f1 = models.DecimalField(_("Commissione su PUN F1 (€/kWh)"), max_digits=6, decimal_places=4, default=0.02, 
        help_text=_("Commissione aggiuntiva rispetto al PUN per fascia F1 (ore di punta: Lun-Ven 8-19)"))
    pun_fee_f2 = models.DecimalField(_("Commissione su PUN F2 (€/kWh)"), max_digits=6, decimal_places=4, default=0.02,
        help_text=_("Commissione aggiuntiva rispetto al PUN per fascia F2 (ore intermedie: Lun-Ven 7-8/19-23, Sab 7-23)"))
    pun_fee_f3 = models.DecimalField(_("Commissione su PUN F3 (€/kWh)"), max_digits=6, decimal_places=4, default=0.02,
        help_text=_("Commissione aggiuntiva rispetto al PUN per fascia F3 (notti, domeniche e festivi)"))
    
    # Costi fissi
    connection_fee = models.DecimalField(_("Costo fisso di connessione (€/mese)"), max_digits=10, decimal_places=2, default=50.0)
    power_fee = models.DecimalField(_("Costo potenza impegnata (€/kW/mese)"), max_digits=6, decimal_places=2, default=1.5)
    
    # Date validità
    valid_from = models.DateField(_("Valido dal"))
    valid_to = models.DateField(_("Valido fino al"), blank=True, null=True)
    
    notes = models.TextField(_("Note"), blank=True)
    
    def __str__(self):
        return f"{self.name} - {self.provider}"
    
    def get_current_energy_cost(self, power_kw=None, date=None, hour=None, use_projections=True):
        """
        Calcola il costo attuale dell'energia in base al tipo di tariffa.
        Per tariffe indicizzate PUN, usa i dati PUN più recenti o proiezioni.
        """
        from datetime import datetime
        
        # Se è una tariffa a prezzo fisso, usa i tier in base alla potenza
        if self.tariff_type == 'fixed':
            if not power_kw:
                return float(self.cost_tier2)  # Default tier
                
            if power_kw <= 7:
                return float(self.cost_tier1)
            elif power_kw <= 22:
                return float(self.cost_tier2)
            elif power_kw <= 50:
                return float(self.cost_tier3)
            elif power_kw <= 150:
                return float(self.cost_tier4)
            else:
                return float(self.cost_tier5)
        
        # Per tariffe indicizzate PUN
        if self.tariff_type == 'pun':
            current_date = date or datetime.now().date()
            current_hour = hour or datetime.now().hour
            
            # Determina la fascia oraria
            timeband = PunData.get_timeband(current_date, current_hour)
            
            # Ottieni la commissione corretta in base alla fascia oraria
            if timeband == 'F1':
                commission = float(self.pun_fee_f1)
            elif timeband == 'F2':
                commission = float(self.pun_fee_f2)
            else:  # F3
                commission = float(self.pun_fee_f3)
            
            # Cerca il dato PUN più recente per questa fascia
            latest_pun = PunData.objects.filter(timeband=timeband).order_by('-date', '-hour').first()
            
            # Se esiste un dato PUN recente, usalo
            if latest_pun:
                pun_price = float(latest_pun.price) / 1000  # Converti da €/MWh a €/kWh
                return pun_price + commission
            
            # Se non ci sono dati PUN recenti ma è richiesta una proiezione
            if use_projections:
                # Cerca la proiezione più recente per l'anno/mese corrente o futuri
                projection = EnergyPriceProjection.objects.filter(
                    year__gte=current_date.year,
                    month__gte=current_date.month if current_date.year == datetime.now().year else 1
                ).order_by('year', 'month').first()
                
                if projection:
                    if timeband == 'F1':
                        base_price = float(projection.f1_price)
                    elif timeband == 'F2':
                        base_price = float(projection.f2_price)
                    else:  # F3
                        base_price = float(projection.f3_price)
                    return base_price + commission
            
            # Fallback se non ci sono dati PUN né proiezioni
            # Usa un valore medio PUN stimato più la commissione
            default_pun_prices = {'F1': 0.15, 'F2': 0.13, 'F3': 0.11}  # valori medi stimati in €/kWh
            return default_pun_prices.get(timeband, 0.13) + commission
    
    class Meta:
        verbose_name = _("Tariffa elettrica")
        verbose_name_plural = _("Tariffe elettriche")
        ordering = ["-active", "name"]

class ManagementFee(models.Model):
    name = models.CharField(_("Nome configurazione"), max_length=100)
    active = models.BooleanField(_("Attiva"), default=True)
    
    # Commissioni di gestione
    session_fee = models.DecimalField(_("Commissione fissa per sessione (€)"), max_digits=6, decimal_places=2, default=0.5)
    percentage_fee = models.DecimalField(_("Commissione percentuale (%)"), max_digits=5, decimal_places=2, default=5.0)
    monthly_fee = models.DecimalField(_("Canone mensile (€)"), max_digits=8, decimal_places=2, default=20.0)
    
    # Prezzi per il cliente finale
    customer_price_tier1 = models.DecimalField(_("Prezzo cliente €/kWh (≤ 7kW)"), max_digits=6, decimal_places=4, default=0.4)
    customer_price_tier2 = models.DecimalField(_("Prezzo cliente €/kWh (≤ 22kW)"), max_digits=6, decimal_places=4, default=0.5)
    customer_price_tier3 = models.DecimalField(_("Prezzo cliente €/kWh (≤ 50kW)"), max_digits=6, decimal_places=4, default=0.6)
    customer_price_tier4 = models.DecimalField(_("Prezzo cliente €/kWh (≤ 150kW)"), max_digits=6, decimal_places=4, default=0.7)
    customer_price_tier5 = models.DecimalField(_("Prezzo cliente €/kWh (> 150kW)"), max_digits=6, decimal_places=4, default=0.8)
    
    # Date validità
    valid_from = models.DateField(_("Valido dal"))
    valid_to = models.DateField(_("Valido fino al"), blank=True, null=True)
    
    notes = models.TextField(_("Note"), blank=True)
    
    def __str__(self):
        return self.name
    
    def calculate_margin(self, electricity_tariff, power_kw):
        """Calcola il margine per kWh in base alla tariffa elettrica e alla potenza"""
        if not electricity_tariff:
            return None
            
        if power_kw <= 7:
            cost = float(electricity_tariff.cost_tier1)
            price = float(self.customer_price_tier1)
        elif power_kw <= 22:
            cost = float(electricity_tariff.cost_tier2)
            price = float(self.customer_price_tier2)
        elif power_kw <= 50:
            cost = float(electricity_tariff.cost_tier3)
            price = float(self.customer_price_tier3)
        elif power_kw <= 150:
            cost = float(electricity_tariff.cost_tier4)
            price = float(self.customer_price_tier4)
        else:
            cost = float(electricity_tariff.cost_tier5)
            price = float(self.customer_price_tier5)
            
        margin = price - cost
        margin_percentage = (margin / cost) * 100 if cost > 0 else 0
        
        return {
            'cost': cost,
            'price': price,
            'margin': margin,
            'margin_percentage': margin_percentage
        }
    
    class Meta:
        verbose_name = _("Configurazione tariffaria")
        verbose_name_plural = _("Configurazioni tariffarie")
        ordering = ["-active", "name"]


class UsageProfile(models.Model):
    """
    Modello per i profili di utilizzo delle colonnine di ricarica.
    Utilizzato per calcolare i ricavi attesi in base ai parametri di utilizzo.
    """
    LOCATION_TYPES = [
        ('city_center', _('Centro città')),
        ('suburban', _('Periferia/Residenziale')),
        ('commercial', _('Area commerciale')),
        ('highway', _('Autostrada/Superstrada')),
        ('rural', _('Area rurale')),
    ]
    
    name = models.CharField(_('Nome profilo'), max_length=100)
    description = models.TextField(_('Descrizione'), blank=True)
    
    # Parametri di utilizzo
    daily_usage_hours = models.FloatField(_('Ore di utilizzo giornaliere'), default=8.0)
    avg_session_kwh = models.FloatField(_('kWh medi per sessione'), default=15.0)
    utilization_rate = models.FloatField(_('Tasso di utilizzo'), default=0.5)
    suggested_price_kwh = models.FloatField(_('Prezzo suggerito per kWh'), default=0.45)
    location_type = models.CharField(_('Tipo di posizione'), max_length=20, choices=LOCATION_TYPES, default='city_center')
    
    created_at = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Ultima modifica'), auto_now=True)
    
    class Meta:
        verbose_name = _('Profilo di utilizzo')
        verbose_name_plural = _('Profili di utilizzo')
    
    def __str__(self):
        return f"{self.name} ({self.get_location_type_display()})"       

class StationUsageProfile(models.Model):
    name = models.CharField(_("Nome profilo"), max_length=100)
    description = models.TextField(_("Descrizione"), blank=True)
    
    # Ore di utilizzo medie
    weekday_morning_usage = models.IntegerField(_("Utilizzo feriale mattina (%)"), default=30)
    weekday_afternoon_usage = models.IntegerField(_("Utilizzo feriale pomeriggio (%)"), default=50)
    weekday_evening_usage = models.IntegerField(_("Utilizzo feriale sera (%)"), default=20)
    weekend_morning_usage = models.IntegerField(_("Utilizzo weekend mattina (%)"), default=40)
    weekend_afternoon_usage = models.IntegerField(_("Utilizzo weekend pomeriggio (%)"), default=60)
    weekend_evening_usage = models.IntegerField(_("Utilizzo weekend sera (%)"), default=30)
    
    # Profilo cliente
    CUSTOMER_PROFILE_CHOICES = [
        ('commuter', _('Pendolari')),
        ('resident', _('Residenti')),
        ('visitor', _('Visitatori')),
        ('business', _('Aziende')),
        ('mixed', _('Misto')),
    ]
    customer_profile = models.CharField(_("Profilo cliente"), max_length=20, choices=CUSTOMER_PROFILE_CHOICES, default='mixed')
    
    # Durata media sessione (minuti)
    avg_session_duration = models.IntegerField(_("Durata media sessione (min)"), default=45)
    
    # Energia media per sessione (kWh)
    avg_energy_per_session = models.DecimalField(_("Energia media per sessione (kWh)"), max_digits=6, decimal_places=2, default=15.0)
    
    # Sessioni giornaliere medie
    avg_daily_sessions = models.DecimalField(_("Sessioni giornaliere medie"), max_digits=5, decimal_places=2, default=6.0)
    
    def __str__(self):
        return self.name
    
    def calculate_monthly_usage(self, power_kw):
        """Calcola l'utilizzo mensile stimato in kWh"""
        avg_energy = float(self.avg_energy_per_session)
        avg_sessions = float(self.avg_daily_sessions)
        
        # Stima mensile: sessioni giornaliere * energia media * 30 giorni
        monthly_energy = avg_sessions * avg_energy * 30
        
        # Limita l'energia massima in base alla potenza della stazione
        max_monthly_energy = power_kw * 24 * 30 * 0.85  # 85% della capacità massima teorica
        
        return min(monthly_energy, max_monthly_energy)
    
    class Meta:
        verbose_name = _("Profilo di utilizzo")
        verbose_name_plural = _("Profili di utilizzo")

class ChargingStationTemplate(models.Model):
    name = models.CharField(_("Nome template"), max_length=100)
    brand = models.CharField(_("Marca"), max_length=100)
    model = models.CharField(_("Modello"), max_length=100)
    
    CONNECTION_CHOICES = [
        ('ac', _('AC - Corrente Alternata')),
        ('dc', _('DC - Corrente Continua')),
        ('hybrid', _('Ibrido AC/DC')),
    ]
    connection_type = models.CharField(_("Tipo di connessione"), max_length=10, choices=CONNECTION_CHOICES)
    
    power_kw = models.FloatField(_("Potenza (kW)"))
    num_connectors = models.IntegerField(_("Numero di connettori"), default=2)
    
    CONNECTOR_TYPE_CHOICES = [
        ('type1', _('Type 1')),
        ('type2', _('Type 2')),
        ('chademo', _('CHAdeMO')),
        ('ccs', _('CCS')),
        ('tesla', _('Tesla')),
        ('multiple', _('Multipli')),
    ]
    connector_type = models.CharField(_("Tipo di connettore"), max_length=10, choices=CONNECTOR_TYPE_CHOICES, default='type2')
    
    # Costi standard
    purchase_cost = models.DecimalField(_("Costo d'acquisto (€)"), max_digits=10, decimal_places=2)
    installation_cost = models.DecimalField(_("Costo d'installazione standard (€)"), max_digits=10, decimal_places=2)
    maintenance_cost = models.DecimalField(_("Costo manutenzione annuale (€)"), max_digits=10, decimal_places=2, default=0)
    
    # Costi aggiuntivi per connettività
    modem_4g_cost = models.DecimalField(_("Costo modem 4G (€)"), max_digits=8, decimal_places=2, default=0, help_text=_("Costo aggiuntivo per il modem 4G se richiesto"))
    sim_annual_cost = models.DecimalField(_("Costo annuale SIM dati (€)"), max_digits=8, decimal_places=2, default=0, help_text=_("Costo annuale per la SIM dati se richiesta"))
    
    # Specifiche tecniche
    dimensions = models.CharField(_("Dimensioni"), max_length=100, blank=True)
    weight = models.FloatField(_("Peso (kg)"), blank=True, null=True)
    ground_area = models.DecimalField(_("Superficie occupata (mq)"), max_digits=6, decimal_places=2, blank=True, null=True, help_text=_("Area occupata sul terreno in mq, utile per il calcolo della tassa di occupazione"))
    protection_rating = models.CharField(_("Grado di protezione IP"), max_length=10, blank=True)
    
    # Funzionalità
    has_display = models.BooleanField(_("Display"), default=True)
    has_rfid = models.BooleanField(_("Lettore RFID"), default=True)
    has_app_control = models.BooleanField(_("Controllo da app"), default=True)
    has_lan = models.BooleanField(_("Connessione LAN"), default=True)
    has_wifi = models.BooleanField(_("Connessione WiFi"), default=False)
    has_4g = models.BooleanField(_("Connessione 4G"), default=False)
    
    # Descrizione e note
    description = models.TextField(_("Descrizione"), blank=True)
    technical_specs = models.TextField(_("Specifiche tecniche"), blank=True)
    
    # Immagine
    image = models.ImageField(_("Immagine"), upload_to='station_templates/', blank=True, null=True)
    
    def __str__(self):
        return f"{self.brand} {self.model} - {self.power_kw}kW"
    
    def calculate_total_cost(self):
        """Calcola il costo totale di acquisto, incluso il modem 4G se necessario"""
        total = self.purchase_cost + self.installation_cost
        if self.has_4g:
            # Ottieni il costo del modem dalle impostazioni globali se disponibile
            settings = GlobalSettings.get_active()
            modem_cost = settings.modem_4g_cost if self.modem_4g_cost == 0 else self.modem_4g_cost
            total += modem_cost
        return total
    
    def calculate_annual_cost(self):
        """Calcola il costo annuale di manutenzione, inclusa la SIM dati se necessaria"""
        annual = self.maintenance_cost
        if self.has_4g:
            # Ottieni il costo della SIM dalle impostazioni globali se disponibile
            settings = GlobalSettings.get_active()
            sim_cost = settings.sim_data_cost_monthly * 12 if self.sim_annual_cost == 0 else self.sim_annual_cost
            annual += sim_cost
        return annual
    
    class Meta:
        verbose_name = _("Template stazione di ricarica")
        verbose_name_plural = _("Template stazioni di ricarica")
        ordering = ["brand", "model", "power_kw"]

class ProjectTask(models.Model):
    project = models.ForeignKey(
        ChargingProject, 
        on_delete=models.CASCADE,
        related_name="tasks",
        verbose_name=_("Progetto")
    )
    name = models.CharField(_("Nome attività"), max_length=200)
    description = models.TextField(_("Descrizione"), blank=True)
    
    planned_start_date = models.DateField(_("Data di inizio pianificata"))
    planned_end_date = models.DateField(_("Data di fine pianificata"))
    
    actual_start_date = models.DateField(_("Data di inizio effettiva"), blank=True, null=True)
    actual_end_date = models.DateField(_("Data di fine effettiva"), blank=True, null=True)
    
    PRIORITY_CHOICES = [
        ('low', _('Bassa')),
        ('medium', _('Media')),
        ('high', _('Alta')),
    ]
    priority = models.CharField(_("Priorità"), max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    STATUS_CHOICES = [
        ('not_started', _('Non iniziata')),
        ('in_progress', _('In corso')),
        ('completed', _('Completata')),
        ('delayed', _('In ritardo')),
        ('cancelled', _('Annullata')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    dependencies = models.ManyToManyField(
        'self', 
        blank=True,
        symmetrical=False,
        related_name='dependent_tasks',
        verbose_name=_("Dipendenze")
    )
    
    responsible = models.CharField(_("Responsabile"), max_length=100, blank=True)
    
    class Meta:
        verbose_name = _("Attività di progetto")
        verbose_name_plural = _("Attività di progetto")
        ordering = ["planned_start_date", "planned_end_date"]
    
    def __str__(self):
        return f"{self.name} - {self.project.name}"
    
    def is_delayed(self):
        """Verifica se l'attività è in ritardo"""
        from datetime import date
        if self.status == 'completed':
            return False
        return date.today() > self.planned_end_date
    
    def completion_percentage(self):
        """Calcola la percentuale di completamento dell'attività"""
        if self.status == 'completed':
            return 100
        elif self.status == 'not_started':
            return 0
        elif self.status == 'cancelled':
            return 0
        
        # Se l'attività è in corso, stima la percentuale in base al tempo trascorso
        from datetime import date
        if not self.actual_start_date:
            return 0
        
        total_days = (self.planned_end_date - self.actual_start_date).days
        if total_days <= 0:
            return 50  # Default se le date non sono valide
            
        elapsed_days = (date.today() - self.actual_start_date).days
        percentage = (elapsed_days / total_days) * 100
        
        return min(int(percentage), 99)  # Max 99% se non è completata