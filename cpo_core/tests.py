from django.test import TestCase
from decimal import Decimal
from cpo_core.models.charging_station import ChargingStation
from cpo_core.models.project import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.municipality import Municipality
from cpo_core.models.organization import Organization

class ChargingStationCalculationTest(TestCase):
    """Test per i calcoli di utilizzo e guadagno della stazione di ricarica"""
    
    def setUp(self):
        """Crea dati di test necessari"""
        # Creiamo un'organizzazione
        self.organization = Organization.objects.create(
            name="Test Organization",
            tax_id="12345678901",
            address="Test Address",
            contact_email="test@example.com",
            contact_phone="1234567890"
        )
        
        # Creiamo un municipio
        self.municipality = Municipality.objects.create(
            name="Test Municipality",
            province="Test Province",
            region="Test Region"
        )
        
        # Creiamo un progetto
        self.project = Project.objects.create(
            name="Test Project",
            organization=self.organization
        )
        
        # Creiamo un sottoprogetto
        self.subproject = SubProject.objects.create(
            name="Test SubProject",
            project=self.project,
            municipality=self.municipality
        )
        
        # Creiamo una stazione di ricarica con valori noti
        self.charging_station = ChargingStation.objects.create(
            subproject=self.subproject,
            name="Test Charging Station",
            identifier="CS-TEST-01",
            station_type="ac_fast",
            power_type="ac",
            power_kw=Decimal("22.0"),
            station_cost=Decimal("10000.00"),
            installation_cost=Decimal("2000.00"),
            connection_cost=Decimal("1000.00"),
            energy_cost_kwh=Decimal("0.25"),
            charging_price_kwh=Decimal("0.45"),
            estimated_sessions_day=Decimal("5.0"),
            avg_kwh_session=Decimal("15.0")
        )
    
    def test_calculate_annual_metrics(self):
        """Verifica se il calcolo dei ricavi annuali è corretto"""
        # Ricavi giornalieri = 0.45 € * 15 kWh * 5 sessioni = 33.75 €
        # Ricavi annuali = 33.75 € * 365 = 12,318.75 €
        # Costi energia giornalieri = 0.25 € * 15 kWh * 5 sessioni = 18.75 €
        # Costi energia annuali = 18.75 € * 365 = 6,843.75 €
        # Costi manutenzione annuali = 10,000 € * 0.05 = 500 €
        # Costi totali annuali = 6,843.75 € + 500 € = 7,343.75 €
        # Profitto annuale = 12,318.75 € - 7,343.75 € = 4,975 €
        
        metrics = self.charging_station.calculate_annual_metrics()
        
        # Verifichiamo che i calcoli siano corretti
        expected_annual_revenue = Decimal("33.75") * 365
        self.assertAlmostEqual(
            metrics['annual_revenue'], 
            expected_annual_revenue, 
            delta=Decimal("0.01"),
            msg="I ricavi annuali calcolati non corrispondono al valore atteso"
        )
        
        expected_annual_costs = (Decimal("18.75") * 365) + (self.charging_station.station_cost * Decimal("0.05"))
        self.assertAlmostEqual(
            metrics['annual_costs'], 
            expected_annual_costs, 
            delta=Decimal("0.01"),
            msg="I costi annuali calcolati non corrispondono al valore atteso"
        )
        
        expected_annual_profit = expected_annual_revenue - expected_annual_costs
        self.assertAlmostEqual(
            metrics['annual_profit'], 
            expected_annual_profit, 
            delta=Decimal("0.01"),
            msg="Il profitto annuale calcolato non corrisponde al valore atteso"
        )
    
    def test_calculate_annual_metrics_with_different_values(self):
        """Verifica il calcolo con valori diversi"""
        # Modifichiamo i valori della stazione
        self.charging_station.energy_cost_kwh = Decimal("0.30")
        self.charging_station.charging_price_kwh = Decimal("0.50")
        self.charging_station.estimated_sessions_day = Decimal("7.0")
        self.charging_station.avg_kwh_session = Decimal("12.0")
        self.charging_station.save()
        
        # Ricavi giornalieri = 0.50 € * 12 kWh * 7 sessioni = 42.00 €
        # Ricavi annuali = 42.00 € * 365 = 15,330.00 €
        # Costi energia giornalieri = 0.30 € * 12 kWh * 7 sessioni = 25.20 €
        # Costi energia annuali = 25.20 € * 365 = 9,198.00 €
        # Costi manutenzione annuali = 10,000 € * 0.05 = 500 €
        # Costi totali annuali = 9,198.00 € + 500 € = 9,698.00 €
        # Profitto annuale = 15,330.00 € - 9,698.00 € = 5,632.00 €
        
        metrics = self.charging_station.calculate_annual_metrics()
        
        # Verifichiamo che i calcoli siano corretti
        expected_annual_revenue = Decimal("42.00") * 365
        self.assertAlmostEqual(
            metrics['annual_revenue'], 
            expected_annual_revenue, 
            delta=Decimal("0.01"),
            msg="I ricavi annuali calcolati non corrispondono al valore atteso"
        )
        
        expected_annual_costs = (Decimal("25.20") * 365) + (self.charging_station.station_cost * Decimal("0.05"))
        self.assertAlmostEqual(
            metrics['annual_costs'], 
            expected_annual_costs, 
            delta=Decimal("0.01"),
            msg="I costi annuali calcolati non corrispondono al valore atteso"
        )
        
        expected_annual_profit = expected_annual_revenue - expected_annual_costs
        self.assertAlmostEqual(
            metrics['annual_profit'], 
            expected_annual_profit, 
            delta=Decimal("0.01"),
            msg="Il profitto annuale calcolato non corrisponde al valore atteso"
        )
