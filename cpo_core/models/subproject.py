from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from infrastructure.models import StationUsageProfile

class StationImage(models.Model):
    """Immagini delle stazioni di ricarica"""
    subproject = models.ForeignKey('SubProject', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='charging_stations/', blank=True, null=True)
    title = models.CharField(_("Titolo"), max_length=100, blank=True, null=True)
    description = models.TextField(_("Descrizione"), blank=True, null=True)
    is_before_installation = models.BooleanField(_("Prima dell'installazione"), default=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Immagine per {self.subproject.name} - {self.title or 'Senza titolo'}"
    
    class Meta:
        verbose_name = _("Immagine Stazione")
        verbose_name_plural = _("Immagini Stazioni")
        
class Charger(models.Model):
    """Singola colonnina all'interno di una stazione di ricarica"""
    subproject = models.ForeignKey('SubProject', on_delete=models.CASCADE, related_name='chargers', null=True, blank=True)
    charging_station = models.ForeignKey('ChargingStation', on_delete=models.CASCADE, related_name='chargers', null=True, blank=True)
    
    # Dati colonnina
    code = models.CharField(_("Codice colonnina"), max_length=100)
    brand = models.CharField(_("Marca"), max_length=100, blank=True, null=True)
    model = models.CharField(_("Modello"), max_length=100, blank=True, null=True)
    power_kw = models.DecimalField(_("Potenza (kW)"), max_digits=8, decimal_places=2, null=True, blank=True)
    serial_number = models.CharField(_("Numero seriale"), max_length=100, blank=True, null=True)
    
    # Connettori
    num_connectors = models.PositiveIntegerField(_("Numero Connettori"), default=1)
    connector_types = models.CharField(_("Tipi di Connettori"), max_length=255, blank=True, null=True,
                                 help_text=_("Separati da virgola, esempio: Type 2, CCS, CHAdeMO"))
    
    # Costi
    purchase_cost = models.DecimalField(_("Costo d'acquisto (€)"), max_digits=10, decimal_places=2, null=True, blank=True)
    installation_cost = models.DecimalField(_("Costo d'installazione (€)"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stato
    STATUS_CHOICES = [
        ('operational', _('Operativa')),
        ('maintenance', _('In Manutenzione')),
        ('offline', _('Non Operativa')),
        ('planned', _('Pianificata')),
        ('installing', _('In Installazione')),
    ]
    status = models.CharField(_("Stato"), max_length=20, choices=STATUS_CHOICES, default='planned')
    
    # Date
    installation_date = models.DateField(_("Data installazione"), null=True, blank=True)
    activation_date = models.DateField(_("Data attivazione"), null=True, blank=True)
    
    # Specifiche tecniche
    is_fast_charging = models.BooleanField(_("Ricarica rapida"), default=False)
    is_smart_charging = models.BooleanField(_("Smart charging"), default=False)
    has_display = models.BooleanField(_("Display"), default=True)
    has_rfid = models.BooleanField(_("Lettore RFID"), default=True)
    has_app_control = models.BooleanField(_("Controllo da app"), default=True)
    has_load_balancing = models.BooleanField(_("Load balancing"), default=False)
    
    def __str__(self):
        return f"{self.code} - {self.brand} {self.model}, {self.power_kw}kW"
    
    class Meta:
        verbose_name = _("Colonnina")
        verbose_name_plural = _("Colonnine")
        ordering = ["code"]

class SubProject(models.Model):
    """Sotto-progetto per un comune specifico"""
    # Relazioni
    project = models.ForeignKey('Project', on_delete=models.CASCADE, related_name='subprojects', verbose_name=_('Progetto Principale'))
    municipality = models.ForeignKey('Municipality', on_delete=models.CASCADE, related_name='subprojects', verbose_name=_('Comune'))
    
    # Informazioni di base
    name = models.CharField(_("Nome Sottoprogetto"), max_length=255)
    description = models.TextField(_("Descrizione"), blank=True, null=True)
    
    # Localizzazione
    address = models.CharField(_("Indirizzo"), max_length=255, blank=True, null=True)
    cadastral_data = models.CharField(_("Dati Catastali"), max_length=255, blank=True, null=True, 
                                    help_text=_("Foglio, Particella, Subalterno"))
    latitude_proposed = models.DecimalField(_("Latitudine Proposta"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_proposed = models.DecimalField(_("Longitudine Proposta"), max_digits=9, decimal_places=6, null=True, blank=True)
    latitude_approved = models.DecimalField(_("Latitudine Approvata"), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude_approved = models.DecimalField(_("Longitudine Approvata"), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Giorni di indisponibilità
    WEEKDAY_CHOICES = [
        (0, _('Lunedì')),
        (1, _('Martedì')),
        (2, _('Mercoledì')),
        (3, _('Giovedì')),
        (4, _('Venerdì')),
        (5, _('Sabato')),
        (6, _('Domenica')),
    ]
    weekly_market_day = models.IntegerField(_("Giorno del mercato settimanale"), choices=WEEKDAY_CHOICES, null=True, blank=True,
                                          help_text=_("Giorno della settimana in cui si tiene il mercato e la stazione non è disponibile"))
    local_festival_days = models.IntegerField(_("Giorni festa paesana all'anno"), null=True, blank=True, default=0,
                                           help_text=_("Numero di giorni all'anno in cui la stazione non è disponibile per feste locali"))
    # Nuovo campo per i giorni di pioggia
    rainy_days = models.PositiveSmallIntegerField(_("Giorni di Pioggia Previsti/Anno"), default=0,
                                             help_text=_("Giorni di pioggia stimati che riducono l'utilizzo delle colonnine del 30%"))
    
    # Dettagli colonnine
    charger_brand = models.CharField(_("Marca Colonnina"), max_length=100, blank=True, null=True)
    charger_model = models.CharField(_("Modello Colonnina"), max_length=100, blank=True, null=True)
    power_kw = models.DecimalField(_("Potenza (kW)"), max_digits=8, decimal_places=2, null=True, blank=True)
    power_requested = models.DecimalField(_("Potenza Richiesta a E-Distribuzione (kW)"), max_digits=8, decimal_places=2, null=True, blank=True)
    connector_types = models.CharField(_("Tipi di Connettori"), max_length=255, blank=True, null=True,
                                     help_text=_("Separati da virgola, esempio: Type 2, CCS, CHAdeMO"))
    num_connectors = models.PositiveIntegerField(_("Numero Connettori"), default=1)
    num_chargers = models.PositiveIntegerField(_("Numero Colonnine"), default=1)
    ground_area_sqm = models.DecimalField(_("Area Occupata (m²)"), max_digits=6, decimal_places=2, null=True, blank=True)
    usage_profile = models.ForeignKey(StationUsageProfile, on_delete=models.SET_NULL, null=True, blank=True, 
                                    related_name='charging_stations', verbose_name=_('Profilo di Consumo'))
    
    # Timeline
    start_date = models.DateField(_("Data Inizio"), default="2023-01-01")
    planned_completion_date = models.DateField(_("Data Prevista Completamento"), default="2023-12-31")
    actual_completion_date = models.DateField(_("Data Effettiva Completamento"), null=True, blank=True)
    use_project_completion_date = models.BooleanField(_("Usa Data Completamento Progetto"), default=False)
    
    # Informazioni finanziarie
    budget = models.DecimalField(_("Budget Totale"), max_digits=12, decimal_places=2, default=0)
    expected_revenue = models.DecimalField(_("Ricavi Attesi"), max_digits=12, decimal_places=2, default=0)
    roi = models.DecimalField(_("ROI"), max_digits=10, decimal_places=2, default=0, validators=[
        MinValueValidator(Decimal('-99.99')), 
        MaxValueValidator(Decimal('9999.99'))
    ])
    
    # Dettaglio costi
    equipment_cost = models.DecimalField(_("Costo Colonnina"), max_digits=10, decimal_places=2, null=True, blank=True)
    installation_cost = models.DecimalField(_("Costo Installazione"), max_digits=10, decimal_places=2, null=True, blank=True)
    connection_cost = models.DecimalField(_("Costo Allaccio Rete"), max_digits=10, decimal_places=2, null=True, blank=True)
    permit_cost = models.DecimalField(_("Costo Permessi"), max_digits=10, decimal_places=2, null=True, blank=True)
    civil_works_cost = models.DecimalField(_("Costo Opere Civili"), max_digits=10, decimal_places=2, null=True, blank=True)
    other_costs = models.DecimalField(_("Altri Costi"), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Personale
    responsible_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='responsible_for_subprojects', blank=True)
    
    # Stato
    STATUS_CHOICES = [
        ('planning', _('Pianificazione')),
        ('permit', _('Richiesta Permessi')),
        ('approval', _('In Approvazione')),
        ('construction', _('In Costruzione')),
        ('in_progress', _('In Corso')),
        ('operational', _('Operativo')),
        ('maintenance', _('In Manutenzione')),
        ('completed', _('Completato')),
        ('suspended', _('Sospeso')),
        ('closed', _('Chiuso'))
    ]
    status = models.CharField(_("Stato Sotto-Progetto"), max_length=20, choices=STATUS_CHOICES, default='planning')
    status_changed_date = models.DateTimeField(_("Data Cambio Stato"), auto_now=False, null=True, blank=True)
    status_changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                       related_name='status_changes', verbose_name=_('Cambio Stato Da'))
    
    def calculate_availability_factor(self):
        """
        Calcola il fattore di disponibilità basato sui giorni di indisponibilità e sui giorni di pioggia
        """
        # Giorni totali in un anno
        total_days = 365
        
        # Calcola i giorni di indisponibilità totali
        unavailable_days = 0
        
        # Aggiungi i giorni di mercato (52 settimane)
        if self.weekly_market_day is not None:
            unavailable_days += 52
            
        # Aggiungi i giorni di festa locale
        if self.local_festival_days:
            unavailable_days += self.local_festival_days
        
        # Calcolo della disponibilità di base
        available_days = total_days - unavailable_days
        base_availability_factor = available_days / total_days if total_days > 0 else 1.0
        
        # Calcolo dell'impatto dei giorni di pioggia (riduzione del 30%)
        rainy_days_impact = 0
        if self.rainy_days:
            rainy_days_impact = (self.rainy_days * 0.3) / total_days if total_days > 0 else 0
        
        # Fattore di disponibilità finale considerando anche i giorni di pioggia
        availability_factor = base_availability_factor * (1 - rainy_days_impact)
        
        return availability_factor
    
    def save(self, *args, **kwargs):
        # Debug: mostra i valori dei costi prima del salvataggio
        print("DEBUG - SubProject save - Prima del calcolo budget:", {
            'equipment_cost': self.equipment_cost,
            'installation_cost': self.installation_cost, 
            'connection_cost': self.connection_cost,
            'permit_cost': self.permit_cost,
            'civil_works_cost': self.civil_works_cost,
            'other_costs': self.other_costs
        })
    
        # Gestione delle date in base al progetto
        if not self.pk:  # Solo per nuovi oggetti
            if self.start_date < self.project.start_date:
                self.start_date = self.project.start_date
                
            if self.use_project_completion_date:
                self.planned_completion_date = self.project.expected_completion_date
            elif self.planned_completion_date > self.project.expected_completion_date:
                self.planned_completion_date = self.project.expected_completion_date
        
        # Calcola il costo di connessione SOLO se specificato nel form che deve essere calcolato automaticamente
        # Ma non sovrascrivere il valore se è stato impostato manualmente
        # Usiamo un attributo temporaneo per controllare se il calcolo automatico è richiesto
        auto_calculate_connection = getattr(self, '_auto_calculate_connection', False)
        
        if auto_calculate_connection and self.power_requested and (self.connection_cost is None or self.connection_cost == 0):
            self.connection_cost = self.power_requested * 80  # 80€ per kW
            print(f"DEBUG - Calcolato automaticamente connection_cost: {self.connection_cost}")
        
        # Calcola il budget totale sommando i costi
        total_cost = sum(filter(None, [
            self.equipment_cost or 0,
            self.installation_cost or 0, 
            self.connection_cost or 0,
            self.permit_cost or 0,
            self.civil_works_cost or 0,
            self.other_costs or 0
        ]))
        
        # Debug: mostra i valori dei costi dopo i calcoli
        print("DEBUG - SubProject save - Dopo il calcolo budget:", {
            'total_cost': total_cost,
            'equipment_cost': self.equipment_cost,
            'installation_cost': self.installation_cost, 
            'connection_cost': self.connection_cost,
            'permit_cost': self.permit_cost,
            'civil_works_cost': self.civil_works_cost,
            'other_costs': self.other_costs
        })
        if total_cost > 0:
            self.budget = total_cost
            
        # Calcola i ricavi attesi e il ROI utilizzando il metodo standardizzato
        from cpo_core.models.charging_station import ChargingStation
        
        if self.power_kw:
            # Assicuriamo che i parametri relativi ai giorni di indisponibilità siano validi
            if self.local_festival_days is None:
                self.local_festival_days = 0
                
            # Assicuriamo che rainy_days sia valido
            if self.rainy_days is None:
                self.rainy_days = 0
                
            # Crea una stazione virtuale temporanea per utilizzare il metodo di calcolo standardizzato
            temp_station = ChargingStation(
                power_kw=self.power_kw,
                charging_price_kwh=Decimal('0.45'),  # Prezzo standard
                avg_kwh_session=Decimal('15.0'),     # kWh per sessione standard
                estimated_sessions_day=Decimal('5.0')  # Sessioni al giorno standard
            )
            
            # Imposta il riferimento al subproject per accedere ai dati di indisponibilità
            temp_station.subproject = self
            
            # Calcola il ricavo annuale utilizzando il metodo standardizzato
            try:
                annual_revenue = temp_station.calculate_annual_revenue(
                    include_availability=True,  # Considera i giorni di indisponibilità
                    include_seasonality=True    # Considera i fattori stagionali
                )
            except Exception as e:
                print(f"DEBUG - Errore nel calcolo ricavi: {e}")
                # Fallback in caso di errore: calcolo più semplice
                daily_revenue = temp_station.charging_price_kwh * temp_station.avg_kwh_session * temp_station.estimated_sessions_day
                
                # Considera il fattore di disponibilità che ora include i giorni di pioggia
                availability_factor = self.calculate_availability_factor()
                annual_revenue = daily_revenue * Decimal('365') * Decimal(str(availability_factor))
            
            # Aggiorna i campi nel modello
            self.expected_revenue = annual_revenue
            
            # Debug info
            print(f"DEBUG - Calcolo ricavi standardizzato: power_kw={self.power_kw}, "
                  f"mercato={self.weekly_market_day}, feste={self.local_festival_days}, "
                  f"pioggia={self.rainy_days}, ricavi={annual_revenue:.2f}")
            
            # Calcolo ROI
            if self.budget and self.budget > 0:
                # ROI annuo = (ricavi annuali / investimento totale) * 100
                # Converti entrambi i valori a Decimal per evitare errori di tipo
                annual_revenue_decimal = Decimal(str(annual_revenue)) if not isinstance(annual_revenue, Decimal) else annual_revenue
                budget_decimal = Decimal(str(self.budget)) if not isinstance(self.budget, Decimal) else self.budget
                self.roi = (annual_revenue_decimal / budget_decimal) * Decimal('100')
        
        super().save(*args, **kwargs)
        # Aggiorna le metriche del progetto principale dopo il salvataggio
        self.project.calculate_total_metrics()
    
    def __str__(self):
        return f"{self.name} - {self.municipality}"
    
    class Meta:
        verbose_name = _("Sotto-Progetto")
        verbose_name_plural = _("Sotto-Progetti")