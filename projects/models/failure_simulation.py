# cpo_planner/projects/models/failure_simulation.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class FailureSimulation(models.Model):
    """
    Modello per la simulazione dei guasti delle colonnine
    """
    project = models.OneToOneField(
        'Project', 
        on_delete=models.CASCADE, 
        related_name='failure_simulation',
        verbose_name=_('Progetto')
    )
    
    # Parametri simulazione
    failure_rate_year1 = models.DecimalField(
        _('Tasso guasti anno 1 (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=1.0,
        help_text=_('Probabilità di guasto nel primo anno')
    )
    
    failure_rate_increase = models.DecimalField(
        _('Incremento annuo tasso guasti (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        default=5.0,
        help_text=_('Incremento percentuale annuo della probabilità di guasto')
    )
    
    minor_repair_percentage = models.DecimalField(
        _('Percentuale riparazioni minori (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=70.0,
        help_text=_('Percentuale di guasti che richiedono riparazioni minori')
    )
    
    major_repair_percentage = models.DecimalField(
        _('Percentuale riparazioni maggiori (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=25.0,
        help_text=_('Percentuale di guasti che richiedono riparazioni maggiori')
    )
    
    replacement_percentage = models.DecimalField(
        _('Percentuale sostituzioni (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=5.0,
        help_text=_('Percentuale di guasti che richiedono sostituzione totale')
    )
    
    minor_repair_cost_percentage = models.DecimalField(
        _('Costo riparazione minore (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=5.0,
        help_text=_('Costo di riparazione minore come % del costo della colonnina')
    )
    
    major_repair_cost_percentage = models.DecimalField(
        _('Costo riparazione maggiore (%)'), 
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=20.0,
        help_text=_('Costo di riparazione maggiore come % del costo della colonnina')
    )
    
    average_downtime_minor = models.PositiveIntegerField(
        _('Tempo fermo medio riparazione minore (giorni)'),
        default=2,
        help_text=_('Giorni medi di inattività per riparazione minore')
    )
    
    average_downtime_major = models.PositiveIntegerField(
        _('Tempo fermo medio riparazione maggiore (giorni)'),
        default=7,
        help_text=_('Giorni medi di inattività per riparazione maggiore')
    )
    
    average_downtime_replacement = models.PositiveIntegerField(
        _('Tempo fermo medio sostituzione (giorni)'),
        default=14,
        help_text=_('Giorni medi di inattività per sostituzione')
    )
    
    # Risultati simulazione
    simulation_results = models.JSONField(
        _('Risultati simulazione'),
        default=dict,
        help_text=_('Risultati dettagliati della simulazione di guasti in formato JSON')
    )
    
    total_failures = models.PositiveIntegerField(
        _('Totale guasti simulati'),
        default=0
    )
    
    total_repair_costs = models.DecimalField(
        _('Costi totali riparazione'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    total_revenue_loss = models.DecimalField(
        _('Perdita totale ricavi'),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    created_at = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Data aggiornamento'), auto_now=True)
    
    def run_simulation(self, years=10):
        """
        Esegue la simulazione dei guasti per il periodo specificato
        """
        from random import random
        
        # Ottieni tutte le stazioni di ricarica associate a questo progetto
        stations = []
        for subproject in self.project.subproject_set.all():
            stations.extend(list(subproject.chargingstation_set.all()))
        
        total_stations = len(stations)
        yearly_results = []
        
        total_failures = 0
        total_repair_costs = Decimal('0.00')
        total_revenue_loss = Decimal('0.00')
        
        # Esegui la simulazione per ogni anno
        for year in range(1, years + 1):
            # Calcola il tasso di guasto per l'anno corrente
            failure_rate = self.failure_rate_year1 * (1 + (self.failure_rate_increase / 100) * (year - 1)) / 100
            
            # Limita il tasso di guasto massimo al 100%
            failure_rate = min(failure_rate, 1.0)
            
            year_failures = 0
            year_repair_costs = Decimal('0.00')
            year_revenue_loss = Decimal('0.00')
            
            # Simula i guasti per ogni stazione
            station_failures = []
            for station in stations:
                # Determina se la stazione avrà un guasto quest'anno
                if random() < failure_rate:
                    # Determina il tipo di guasto
                    failure_type = self._determine_failure_type()
                    
                    # Calcola i costi di riparazione
                    repair_cost = self._calculate_repair_cost(station, failure_type)
                    
                    # Calcola la perdita di ricavi dovuta al downtime
                    downtime = self._get_downtime(failure_type)
                    revenue_loss = self._calculate_revenue_loss(station, downtime)
                    
                    year_failures += 1
                    year_repair_costs += repair_cost
                    year_revenue_loss += revenue_loss
                    
                    station_failures.append({
                        'station_id': station.id,
                        'station_name': station.name,
                        'failure_type': failure_type,
                        'repair_cost': float(repair_cost),
                        'downtime_days': downtime,
                        'revenue_loss': float(revenue_loss),
                    })
            
            yearly_results.append({
                'year': year,
                'failure_rate': float(failure_rate),
                'failures': year_failures,
                'repair_costs': float(year_repair_costs),
                'revenue_loss': float(year_revenue_loss),
                'total_stations': total_stations,
                'failure_percentage': year_failures / total_stations * 100 if total_stations > 0 else 0,
                'station_failures': station_failures
            })
            
            total_failures += year_failures
            total_repair_costs += year_repair_costs
            total_revenue_loss += year_revenue_loss
        
        # Aggiorna i campi del modello con i risultati
        self.simulation_results = {
            'yearly_results': yearly_results,
            'summary': {
                'total_failures': total_failures,
                'total_repair_costs': float(total_repair_costs),
                'total_revenue_loss': float(total_revenue_loss),
                'total_impact': float(total_repair_costs + total_revenue_loss),
                'average_yearly_failures': total_failures / years,
                'average_yearly_costs': float(total_repair_costs / years),
                'average_failures_per_station': total_failures / total_stations if total_stations > 0 else 0
            }
        }
        
        self.total_failures = total_failures
        self.total_repair_costs = total_repair_costs
        self.total_revenue_loss = total_revenue_loss
        self.save()
        
        return self.simulation_results
    
    def _determine_failure_type(self):
        """
        Determina il tipo di guasto in base alle probabilità configurate
        """
        from random import random
        
        rand = random() * 100
        
        if rand < self.minor_repair_percentage:
            return 'minor'
        elif rand < (self.minor_repair_percentage + self.major_repair_percentage):
            return 'major'
        else:
            return 'replacement'
    
    def _calculate_repair_cost(self, station, failure_type):
        """
        Calcola il costo di riparazione in base al tipo di guasto
        """
        if failure_type == 'minor':
            return station.station_cost * (self.minor_repair_cost_percentage / 100)
        elif failure_type == 'major':
            return station.station_cost * (self.major_repair_cost_percentage / 100)
        else:  # replacement
            return station.station_cost
    
    def _get_downtime(self, failure_type):
        """
        Restituisce il downtime in base al tipo di guasto
        """
        if failure_type == 'minor':
            return self.average_downtime_minor
        elif failure_type == 'major':
            return self.average_downtime_major
        else:  # replacement
            return self.average_downtime_replacement
    
    def _calculate_revenue_loss(self, station, downtime_days):
        """
        Calcola la perdita di ricavi durante il downtime
        """
        daily_revenue = station.charging_price_kwh * station.avg_kwh_session * station.estimated_sessions_day
        return daily_revenue * downtime_days
    
    def __str__(self):
        return f"Simulazione guasti: {self.project.name}"
    
    class Meta:
        verbose_name = _('Simulazione Guasti')
        verbose_name_plural = _('Simulazioni Guasti')