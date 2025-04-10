# environmental/services.py
import datetime
import logging
import json
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from projects.models import Project, SubProject, ChargingStation
from .models import (
    EnvironmentalAnalysis, YearlyEnvironmentalData,
    EmissionFactor, VehicleType
)

# Configura il logger
logger = logging.getLogger(__name__)

class EnvironmentalCalculator:
    """Servizio per calcolare l'impatto ambientale"""
    
    # Costanti per i calcoli
    TREE_CO2_ABSORPTION = 22  # kg di CO2 assorbiti da un albero in un anno
    
    def __init__(self, analysis):
        """Inizializza il calcolatore con l'analisi da calcolare"""
        self.analysis = analysis
        self.charging_stations = []
        self.vehicle_types = list(VehicleType.objects.all())
        
        # Carica le stazioni di ricarica associate
        self._load_charging_stations()
    
    def _load_charging_stations(self):
        """Carica le stazioni di ricarica associate all'analisi"""
        if not self.analysis.content_type or not self.analysis.object_id:
            # Analisi globale, carica tutte le stazioni
            self.charging_stations = list(ChargingStation.objects.all())
            return
            
        content_type = self.analysis.content_type
        object_id = self.analysis.object_id
        
        if content_type.model == 'project':
            # Carica le stazioni del progetto
            project = Project.objects.get(id=object_id)
            self.charging_stations = list(
                ChargingStation.objects.filter(subproject__project=project)
            )
        elif content_type.model == 'subproject':
            # Carica le stazioni del sotto-progetto
            subproject = SubProject.objects.get(id=object_id)
            self.charging_stations = list(
                ChargingStation.objects.filter(subproject=subproject)
            )
        elif content_type.model == 'chargingstation':
            # Singola stazione
            self.charging_stations = [ChargingStation.objects.get(id=object_id)]
    
    def calculate(self):
        """Calcola l'impatto ambientale"""
        try:
            # Elimina eventuali dati precedenti
            self.analysis.yearly_data.all().delete()
            
            # Calcola il numero totale di punti di ricarica
            total_charging_points = sum(station.charging_points for station in self.charging_stations if station.charging_points)
            
            # Se non ci sono punti di ricarica, non possiamo calcolare l'impatto
            if total_charging_points == 0:
                self.analysis.total_energy_delivered = 0
                self.analysis.total_co2_emissions = 0
                self.analysis.total_co2_saved = 0
                self.analysis.equivalent_trees = 0
                self.analysis.equivalent_ice_km = 0
                self.analysis.save()
                return False
            
            # Calcola l'energia media consegnata per punto di ricarica all'anno
            avg_daily_kwh = (
                self.analysis.avg_sessions_per_day * 
                self.analysis.avg_kwh_per_session *
                (self.analysis.utilization_rate / 100)
            )
            
            avg_yearly_kwh = avg_daily_kwh * 365
            
            # Fattori di emissione
            electricity_ef = self.analysis.electricity_emission_factor.emission_factor  # gCO2/kWh
            fuel_ef = self.analysis.fuel_emission_factor.emission_factor  # gCO2/kWh
            
            # Percentuale di energia rinnovabile
            renewable_ratio = self.analysis.renewable_percentage / 100
            
            # Calcola i dati per ogni anno
            current_year = timezone.now().year
            total_energy_delivered = 0
            total_co2_emissions = 0
            total_co2_saved = 0
            
            for year_index in range(self.analysis.years_projection):
                year = current_year + year_index
                
                # Calcola quanti punti di ricarica sono attivi in questo anno
                active_points = self._calculate_active_points(year, total_charging_points)
                
                # Energia erogata in MWh
                yearly_energy_mwh = (avg_yearly_kwh * active_points) / 1000  # da kWh a MWh
                
                # Emissioni di CO2 dalle ricariche in tonnellate
                # Considera la percentuale di energia rinnovabile
                effective_ef = electricity_ef * (1 - renewable_ratio)
                yearly_emissions_tons = (yearly_energy_mwh * effective_ef) / 1000000  # da gCO2 a tonnellate
                
                # CO2 risparmiata rispetto ai veicoli a combustione interna
                yearly_saved_tons = self._calculate_co2_saved(yearly_energy_mwh, fuel_ef)
                
                # Calcola la distribuzione per tipologia di veicolo
                vehicle_distribution = self._calculate_vehicle_distribution(yearly_energy_mwh)
                
                # Crea l'oggetto dati annuali
                YearlyEnvironmentalData.objects.create(
                    analysis=self.analysis,
                    year=year,
                    energy_delivered=yearly_energy_mwh,
                    co2_emissions=yearly_emissions_tons,
                    co2_saved=yearly_saved_tons,
                    vehicle_distribution=vehicle_distribution
                )
                
                # Aggiorna i totali
                total_energy_delivered += yearly_energy_mwh
                total_co2_emissions += yearly_emissions_tons
                total_co2_saved += yearly_saved_tons
            
            # Aggiorna i totali nell'analisi
            self.analysis.total_energy_delivered = total_energy_delivered
            self.analysis.total_co2_emissions = total_co2_emissions
            self.analysis.total_co2_saved = total_co2_saved
            
            # Calcola gli equivalenti
            self.analysis.equivalent_trees = int(total_co2_saved * 1000 / self.TREE_CO2_ABSORPTION)
            self.analysis.equivalent_ice_km = self._calculate_equivalent_ice_km(total_energy_delivered)
            
            self.analysis.save()
            return True
        
        except Exception as e:
            logger.error(f"Errore nel calcolo dell'impatto ambientale: {str(e)}")
            return False
    
    def _calculate_active_points(self, year, total_points):
        """Calcola quanti punti di ricarica sono attivi nell'anno specificato"""
        current_year = timezone.now().year
        
        # Considera una curva di adozione delle stazioni di ricarica
        # Assumiamo che non tutte le stazioni siano operative dall'inizio
        if year <= current_year:
            # Per l'anno corrente e precedenti, utilizziamo le stazioni già operative
            active_stations = [
                station for station in self.charging_stations 
                if not station.installation_date or station.installation_date.year <= year
            ]
            active_points = sum(station.charging_points for station in active_stations if station.charging_points)
            return active_points
        
        # Per gli anni futuri, stimiamo una crescita
        years_diff = year - current_year
        
        # Supponiamo che tutte le stazioni pianificate saranno operative entro 5 anni
        max_years = 5
        ratio = min(1.0, years_diff / max_years) if max_years > 0 else 1.0
        
        return total_points * (0.5 + 0.5 * ratio)  # Almeno il 50% operativo da subito
    
    def _calculate_co2_saved(self, energy_mwh, fuel_ef):
        """Calcola la CO2 risparmiata rispetto ai veicoli a combustione interna"""
        # Per ogni kWh di energia erogata alle auto elettriche, calcola quanto CO2
        # sarebbe stata emessa da un veicolo ICE equivalente
        
        # Calcola i km percorsi con l'energia erogata
        weighted_ice_emissions = 0
        total_weight = 0
        
        for vehicle_type in self.vehicle_types:
            if vehicle_type.market_share > 0:
                # kWh/km per questo tipo di veicolo
                kwh_per_km = vehicle_type.avg_consumption / 100
                
                # Km percorsi con l'energia erogata
                km = (energy_mwh * 1000) / kwh_per_km  # Da MWh a kWh
                
                # Calcola quanta CO2 avrebbe emesso un veicolo ICE per percorrere gli stessi km
                # L/100km * km / 100 = Litri totali
                ice_liters = (vehicle_type.avg_ice_consumption * km) / 100
                
                # Consideriamo circa 2.3 kg CO2 per litro di benzina (valore medio)
                ice_co2_kg = ice_liters * 2.3
                
                weighted_ice_emissions += ice_co2_kg * (vehicle_type.market_share / 100)
                total_weight += vehicle_type.market_share / 100
        
        if total_weight > 0:
            # Converti da kg a tonnellate
            return weighted_ice_emissions / 1000
        else:
            # Se non abbiamo dati sui veicoli, usiamo una stima semplificata
            # Assumendo un fattore di conversione medio
            energy_kwh = energy_mwh * 1000
            saved_co2_kg = energy_kwh * 0.5  # 0.5 kg CO2 risparmiati per kWh (stima)
            return saved_co2_kg / 1000
    
    def _calculate_equivalent_ice_km(self, total_energy_mwh):
        """Calcola i km equivalenti non percorsi da veicoli ICE"""
        total_energy_kwh = total_energy_mwh * 1000
        
        if not self.vehicle_types:
            # Stima generica se non ci sono dati sui veicoli
            return total_energy_kwh * 5  # Assumiamo 5 km/kWh in media
        
        # Calcola una media ponderata dei km/kWh
        total_km = 0
        total_weight = 0
        
        for vehicle_type in self.vehicle_types:
            if vehicle_type.market_share > 0:
                # km/kWh per questo tipo di veicolo
                km_per_kwh = 100 / vehicle_type.avg_consumption
                
                # Km totali percorsi
                km = total_energy_kwh * km_per_kwh * (vehicle_type.market_share / 100)
                
                total_km += km
                total_weight += vehicle_type.market_share / 100
                
        if total_weight > 0:
            return total_km
        else:
            return total_energy_kwh * 5  # Stima predefinita
    
    def _calculate_vehicle_distribution(self, energy_mwh):
        """Calcola la distribuzione dell'energia erogata per tipo di veicolo"""
        distribution = {}
        
        if not self.vehicle_types:
            return distribution
            
        for vehicle_type in self.vehicle_types:
            if vehicle_type.market_share > 0:
                # Energia allocata a questo tipo di veicolo in base alla quota di mercato
                vehicle_energy = energy_mwh * (vehicle_type.market_share / 100)
                
                # kWh/km per questo tipo di veicolo
                kwh_per_km = vehicle_type.avg_consumption / 100
                
                # Km percorsi
                km = (vehicle_energy * 1000) / kwh_per_km  # Da MWh a kWh
                
                distribution[vehicle_type.name] = {
                    'market_share': vehicle_type.market_share,
                    'energy_mwh': round(vehicle_energy, 2),
                    'km': round(km, 2)
                }
                
        return distribution