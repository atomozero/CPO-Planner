import numpy as np
import numpy_financial as npf
from decimal import Decimal
import random
from datetime import date, timedelta

from ..models.financial import FinancialParameters, FinancialAnalysis


class FinancialAnalysisService:
    """
    Servizio per l'analisi finanziaria e le previsioni di progetti e stazioni di ricarica.
    Calcola ROI, utili, flussi di cassa e simula eventuali guasti.
    """
    
    def __init__(self, project=None, charging_station=None):
        """
        Inizializza il servizio con un progetto o una stazione di ricarica.
        
        Args:
            project: Istanza del modello Project
            charging_station: Istanza del modello ChargingStation
        """
        self.project = project
        self.charging_station = charging_station
        
        if project:
            try:
                self.params = project.financial_parameters
            except FinancialParameters.DoesNotExist:
                self.params = FinancialParameters.objects.create(project=project)
        else:
            self.params = self.charging_station.municipality.project.financial_parameters
            
        self.discount_rate = Decimal('0.08')  # Tasso di sconto per NPV
    
    def calculate_analysis(self):
        """
        Esegue l'analisi finanziaria completa.
        
        Returns:
            FinancialAnalysis: Istanza dell'analisi finanziaria salvata
        """
        if self.project:
            obj, _ = FinancialAnalysis.objects.get_or_create(project=self.project)
        else:
            obj, _ = FinancialAnalysis.objects.get_or_create(charging_station=self.charging_station)
        
        # Calcola l'investimento totale
        total_investment = self._calculate_total_investment()
        obj.total_investment = total_investment
        
        # Calcola flussi di cassa annuali
        yearly_cash_flow = self._calculate_yearly_cash_flow(total_investment)
        obj.yearly_cash_flow = yearly_cash_flow
        
        # Calcola flussi di cassa mensili (primi 24 mesi)
        monthly_cash_flow = self._calculate_monthly_cash_flow(total_investment)
        obj.monthly_cash_flow = monthly_cash_flow
        
        # Calcola piano di ammortamento del prestito
        loan_schedule = self._calculate_loan_schedule()
        obj.loan_schedule = loan_schedule
        
        # Esegui simulazione guasti
        failure_simulation = self._simulate_failures()
        obj.failure_simulation = failure_simulation
        
        # Calcola metriche finanziarie
        npv, irr, payback, roi, pi = self._calculate_financial_metrics(yearly_cash_flow)
        
        obj.net_present_value = npv
        obj.internal_rate_of_return = irr
        obj.payback_period = payback
        obj.return_on_investment = roi
        obj.profitability_index = pi
        
        # Calcola totali
        total_revenue, total_costs = self._calculate_totals(yearly_cash_flow)
        obj.total_revenue = total_revenue
        obj.total_costs = total_costs
        obj.total_profit = total_revenue - total_costs
        
        obj.save()
        return obj
    
    def _calculate_total_investment(self):
        """
        Calcola l'investimento totale iniziale.
        
        Returns:
            Decimal: Investimento totale iniziale
        """
        if self.project:
            total = Decimal('0')
            for municipality in self.project.municipalities.all():
                for station in municipality.charging_stations.all():
                    total += station.total_cost
            return total
        else:
            return self.charging_station.total_cost
    
    def _calculate_yearly_cash_flow(self, total_investment):
        """
        Calcola i flussi di cassa annuali per l'intero periodo di investimento.
        
        Args:
            total_investment: Investimento totale iniziale
            
        Returns:
            dict: Dizionario con i flussi di cassa annuali
        """
        years = self.params.investment_years
        market_growth = float(self.params.market_growth_rate) / 100
        inflation = float(self.params.inflation_rate) / 100
        maintenance_percentage = float(self.params.maintenance_cost_percentage) / 100
        energy_price_increase = float(self.params.energy_price_increase_rate) / 100
        charging_price_increase = float(self.params.charging_price_increase_rate) / 100
        
        # Inizializza struttura dati per i flussi di cassa
        cash_flow = {
            'years': list(range(years + 1)),
            'revenue': [0] * (years + 1),
            'operational_costs': [0] * (years + 1),
            'maintenance_costs': [0] * (years + 1),
            'loan_payments': [0] * (years + 1),
            'net_cash_flow': [0] * (years + 1),
            'cumulative_cash_flow': [0] * (years + 1)
        }
        
        # Anno 0: solo investimento iniziale (negativo)
        cash_flow['net_cash_flow'][0] = -float(total_investment)
        cash_flow['cumulative_cash_flow'][0] = -float(total_investment)
        
        # Parametri iniziali per le stazioni di ricarica
        if self.project:
            stations = []
            for municipality in self.project.municipalities.all():
                stations.extend(list(municipality.charging_stations.all()))
            
            # Raccogli dati iniziali per ogni stazione
            base_revenue = sum(station.calculate_base_revenue() for station in stations)
            base_energy_cost = sum(station.calculate_base_energy_cost() for station in stations)
        else:
            base_revenue = self.charging_station.calculate_base_revenue()
            base_energy_cost = self.charging_station.calculate_base_energy_cost()
        
        # Calcola flussi di cassa per ogni anno
        for year in range(1, years + 1):
            # Aumenti annuali basati sui tassi
            market_factor = (1 + market_growth) ** (year - 1)
            inflation_factor = (1 + inflation) ** (year - 1)
            energy_price_factor = (1 + energy_price_increase) ** (year - 1)
            charging_price_factor = (1 + charging_price_increase) ** (year - 1)
            
            # Calcola ricavi con crescita di mercato e aumento dei prezzi
            yearly_revenue = base_revenue * market_factor * charging_price_factor
            cash_flow['revenue'][year] = round(float(yearly_revenue), 2)
            
            # Calcola costi operativi (principalmente energia)
            yearly_energy_cost = base_energy_cost * market_factor * energy_price_factor
            cash_flow['operational_costs'][year] = round(float(yearly_energy_cost), 2)
            
            # Calcola costi di manutenzione con inflazione
            yearly_maintenance = float(total_investment) * maintenance_percentage * inflation_factor
            cash_flow['maintenance_costs'][year] = round(yearly_maintenance, 2)
            
            # Aggiungi pagamenti del prestito (calcolati separatamente)
            loan_year_payment = self._calculate_loan_payment_for_year(year)
            cash_flow['loan_payments'][year] = round(float(loan_year_payment), 2)
            
            # Calcola flusso di cassa netto
            net_cash = (
                cash_flow['revenue'][year] - 
                cash_flow['operational_costs'][year] - 
                cash_flow['maintenance_costs'][year] - 
                cash_flow['loan_payments'][year]
            )
            cash_flow['net_cash_flow'][year] = round(net_cash, 2)
            
            # Calcola flusso di cassa cumulativo
            cash_flow['cumulative_cash_flow'][year] = round(
                cash_flow['cumulative_cash_flow'][year-1] + net_cash, 2)
        
        return cash_flow
    
    def _calculate_loan_schedule(self):
        """
        Calcola il piano di ammortamento del prestito.
        
        Returns:
            dict: Piano di ammortamento del prestito
        """
        loan_amount = float(self.params.loan_amount)
        interest_rate = float(self.params.loan_interest_rate) / 100
        loan_term = self.params.loan_term
        pre_amortization = self.params.pre_amortization_years
        
        if loan_amount <= 0:
            return {
                'years': [],
                'payment': [],
                'interest': [],
                'principal': [],
                'balance': []
            }
        
        # Inizializza il piano
        schedule = {
            'years': list(range(loan_term + 1)),
            'payment': [0] * (loan_term + 1),
            'interest': [0] * (loan_term + 1),
            'principal': [0] * (loan_term + 1),
            'balance': [0] * (loan_term + 1)
        }
        
        # Anno 0: solo il prestito ottenuto
        schedule['balance'][0] = loan_amount
        
        # Calcola pagamento annuale (dopo preammortamento)
        if loan_term - pre_amortization > 0:
            annual_payment = npf.pmt(
                interest_rate, 
                loan_term - pre_amortization, 
                -loan_amount
            )
        else:
            annual_payment = loan_amount  # Pagamento unico alla fine
        
        # Riempie il piano di ammortamento anno per anno
        for year in range(1, loan_term + 1):
            interest = schedule['balance'][year-1] * interest_rate
            schedule['interest'][year] = round(interest, 2)
            
            if year <= pre_amortization:
                # Durante preammortamento: paghi solo interessi
                schedule['payment'][year] = round(interest, 2)
                schedule['principal'][year] = 0
                schedule['balance'][year] = schedule['balance'][year-1]
            else:
                # Dopo preammortamento: paghi rata completa
                schedule['payment'][year] = round(annual_payment, 2)
                schedule['principal'][year] = round(annual_payment - interest, 2)
                schedule['balance'][year] = round(schedule['balance'][year-1] - schedule['principal'][year], 2)
        
        return schedule
    
    def _calculate_loan_payment_for_year(self, year):
        """
        Calcola il pagamento del prestito per un anno specifico.
        
        Args:
            year: Anno per cui calcolare il pagamento
            
        Returns:
            Decimal: Pagamento del prestito per l'anno specificato
        """
        loan_amount = float(self.params.loan_amount)
        if loan_amount <= 0:
            return Decimal('0')
            
        loan_schedule = self._calculate_loan_schedule()
        if year < len(loan_schedule['payment']):
            return Decimal(str(loan_schedule['payment'][year]))
        return Decimal('0')
    
    def _calculate_loan_payment_for_month(self, month):
        """
        Calcola il pagamento mensile del prestito.
        
        Args:
            month: Mese per cui calcolare il pagamento
            
        Returns:
            Decimal: Pagamento del prestito per il mese specificato
        """
        year = (month - 1) // 12 + 1
        yearly_payment = self._calculate_loan_payment_for_year(year)
        monthly_payment = yearly_payment / 12
        return monthly_payment
        
    def _simulate_failures(self):
        """
        Simula guasti casuali delle colonnine nell'arco dei 10 anni.
        
        Returns:
            dict: Risultati della simulazione di guasti
        """
        years = self.params.investment_years
        failure_prob = float(self.params.failure_probability) / 100
        repair_cost_perc = float(self.params.repair_cost_percentage) / 100
        
        # Inizializza struttura dati per la simulazione
        simulation = {
            'years': list(range(1, years + 1)),
            'failures': [0] * years,
            'repair_costs': [0] * years,
            'active_stations': [0] * years
        }
        
        if self.project:
            stations = []
            for municipality in self.project.municipalities.all():
                stations.extend(list(municipality.charging_stations.all()))
            
            # Inizializza stato delle stazioni (tutte attive)
            station_states = [True] * len(stations)
            station_costs = [float(s.station_cost) for s in stations]
            
            # Per ogni anno, simula guasti
            for year in range(years):
                simulation['active_stations'][year] = sum(station_states)
                failures = 0
                repair_cost = 0
                
                # Per ogni stazione, verifica se si guasta
                for i, active in enumerate(station_states):
                    if active and random.random() < failure_prob:
                        failures += 1
                        repair_cost += station_costs[i] * repair_cost_perc
                        
                        # 10% di probabilità che la stazione non sia riparabile
                        if random.random() < 0.1:
                            station_states[i] = False
                
                simulation['failures'][year] = failures
                simulation['repair_costs'][year] = round(repair_cost, 2)
        else:
            # Singola stazione
            station_cost = float(self.charging_station.station_cost)
            active = True
            
            # Per ogni anno, simula guasti
            for year in range(years):
                simulation['active_stations'][year] = 1 if active else 0
                
                if active and random.random() < failure_prob:
                    simulation['failures'][year] = 1
                    simulation['repair_costs'][year] = round(station_cost * repair_cost_perc, 2)
                    
                    # 10% di probabilità che la stazione non sia riparabile
                    if random.random() < 0.1:
                        active = False
                else:
                    simulation['failures'][year] = 0
                    simulation['repair_costs'][year] = 0
        
        return simulation
    
    def _calculate_financial_metrics(self, cash_flow):
        """
        Calcola le principali metriche finanziarie basate sui flussi di cassa.
        
        Args:
            cash_flow: Dizionario con i flussi di cassa annuali
            
        Returns:
            tuple: (NPV, IRR, Payback, ROI, PI) 
        """
        # Estrai flussi di cassa netti
        net_cash_flows = np.array(cash_flow['net_cash_flow'])
        
        # Calcola NPV
        discount_rate = float(self.discount_rate)
        npv = npf.npv(discount_rate, net_cash_flows)
        
        # Calcola IRR (gestisce gli errori)
        try:
            irr = npf.irr(net_cash_flows)
            if np.isnan(irr):
                irr = 0
        except:
            irr = 0
        
        # Calcola periodo di payback
        cumulative = np.array(cash_flow['cumulative_cash_flow'])
        if np.all(cumulative <= 0):
            payback = float(self.params.investment_years)
        else:
            # Trova l'anno in cui il flusso di cassa cumulativo diventa positivo
            positive_years = np.where(cumulative > 0)[0]
            if len(positive_years) > 0:
                first_positive = positive_years[0]
                if first_positive > 0:
                    # Interpola per ottenere un valore più preciso
                    prev_value = cumulative[first_positive - 1]
                    curr_value = cumulative[first_positive]
                    
                    if curr_value - prev_value != 0:
                        fraction = -prev_value / (curr_value - prev_value)
                        payback = first_positive - 1 + fraction
                    else:
                        payback = first_positive
                else:
                    payback = 0
            else:
                payback = float(self.params.investment_years)
        
        # Calcola ROI
        total_investment = -net_cash_flows[0]
        if total_investment > 0:
            net_profit = sum(net_cash_flows[1:])
            roi = (net_profit / total_investment) * 100
        else:
            roi = 0
        
        # Calcola indice di redditività (PI)
        if total_investment > 0:
            pi = (npv + total_investment) / total_investment
        else:
            pi = 0
        
        return (
            Decimal(str(round(npv, 2))),
            Decimal(str(round(irr * 100, 2))),
            Decimal(str(round(payback, 2))),
            Decimal(str(round(roi, 2))),
            Decimal(str(round(pi, 2)))
        )
    
    def _calculate_totals(self, cash_flow):
        """
        Calcola i totali delle entrate e delle uscite.
        
        Args:
            cash_flow: Dizionario con i flussi di cassa annuali
            
        Returns:
            tuple: (Totale entrate, Totale uscite)
        """
        total_revenue = sum(cash_flow['revenue'])
        
        total_costs = (
            sum(cash_flow['operational_costs']) + 
            sum(cash_flow['maintenance_costs']) + 
            sum(cash_flow['loan_payments'])
        )
        
        return Decimal(str(round(total_revenue, 2))), Decimal(str(round(total_costs, 2)))
        
    def _calculate_monthly_cash_flow(self, total_investment):
        """
        Calcola i flussi di cassa mensili per i primi 24 mesi.
        
        Args:
            total_investment: Investimento totale iniziale
            
        Returns:
            dict: Dizionario con i flussi di cassa mensili
        """
        months = 24  # Primi 24 mesi
        market_growth = float(self.params.market_growth_rate) / 100 / 12  # Mensile
        inflation = float(self.params.inflation_rate) / 100 / 12  # Mensile
        maintenance_percentage = float(self.params.maintenance_cost_percentage) / 100 / 12  # Mensile
        energy_price_increase = float(self.params.energy_price_increase_rate) / 100 / 12  # Mensile
        charging_price_increase = float(self.params.charging_price_increase_rate) / 100 / 12  # Mensile
        
        # Date per i mesi
        today = date.today()
        month_dates = [(today + timedelta(days=30*m)).strftime('%Y-%m') for m in range(months + 1)]
        
        # Inizializza struttura dati per i flussi di cassa
        cash_flow = {
            'months': month_dates,
            'revenue': [0] * (months + 1),
            'operational_costs': [0] * (months + 1),
            'maintenance_costs': [0] * (months + 1),
            'loan_payments': [0] * (months + 1),
            'net_cash_flow': [0] * (months + 1),
            'cumulative_cash_flow': [0] * (months + 1)
        }
        
        # Mese 0: solo investimento iniziale (negativo)
        cash_flow['net_cash_flow'][0] = -float(total_investment)
        cash_flow['cumulative_cash_flow'][0] = -float(total_investment)
        
        # Parametri iniziali per le stazioni di ricarica
        if self.project:
            stations = []
            for municipality in self.project.municipalities.all():
                stations.extend(list(municipality.charging_stations.all()))
            
            # Raccogli dati iniziali per ogni stazione
            base_revenue = sum(station.calculate_base_revenue() for station in stations) / 12  # Mensile
            base_energy_cost = sum(station.calculate_base_energy_cost() for station in stations) / 12  # Mensile
        else:
            base_revenue = self.charging_station.calculate_base_revenue() / 12  # Mensile
            base_energy_cost = self.charging_station.calculate_base_energy_cost() / 12  # Mensile
        
        # Calcola flussi di cassa per ogni mese
        for month in range(1, months + 1):
            # Aumenti mensili basati sui tassi
            market_factor = (1 + market_growth) ** (month - 1)
            inflation_factor = (1 + inflation) ** (month - 1)
            energy_price_factor = (1 + energy_price_increase) ** (month - 1)
            charging_price_factor = (1 + charging_price_increase) ** (month - 1)
            
            # Calcola ricavi con crescita di mercato e aumento dei prezzi
            monthly_revenue = base_revenue * market_factor * charging_price_factor
            cash_flow['revenue'][month] = round(float(monthly_revenue), 2)
            
            # Calcola costi operativi (principalmente energia)
            monthly_energy_cost = base_energy_cost * market_factor * energy_price_factor
            cash_flow['operational_costs'][month] = round(float(monthly_energy_cost), 2)
            
            # Calcola costi di manutenzione con inflazione
            monthly_maintenance = float(total_investment) * maintenance_percentage * inflation_factor
            cash_flow['maintenance_costs'][month] = round(monthly_maintenance, 2)
            
            # Aggiungi pagamenti del prestito (calcolati separatamente)
            loan_month_payment = self._calculate_loan_payment_for_month(month)
            cash_flow['loan_payments'][month] = round(float(loan_month_payment), 2)
            
            # Calcola flusso di cassa netto
            net_cash = (
                cash_flow['revenue'][month] - 
                cash_flow['operational_costs'][month] - 
                cash_flow['maintenance_costs'][month] - 
                cash_flow['loan_payments'][month]
            )
            cash_flow['net_cash_flow'][month] = round(net_cash, 2)
            
            # Calcola flusso di cassa cumulativo
            cash_flow['cumulative_cash_flow'][month] = round(
                cash_flow['cumulative_cash_flow'][month-1] + net_cash, 2)
        
        return cash_flow
            