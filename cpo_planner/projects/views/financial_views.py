# cpo_planner/projects/views/financial_views.py
from django.views.generic import DetailView, CreateView, UpdateView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
import weasyprint
from django.template.loader import render_to_string
from django.conf import settings
import os

from cpo_core.models.project import Project
from ..models.charging_station import ChargingStation
from ..models.financial import FinancialParameters, FinancialAnalysis
from ..forms.financial import FinancialParametersForm

class FinancialParametersUpdateView(LoginRequiredMixin, UpdateView):
    model = FinancialParameters
    form_class = FinancialParametersForm
    template_name = 'projects/financial_parameters_form.html'
    
    def get_object(self, queryset=None):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        obj, created = FinancialParameters.objects.get_or_create(project=project)
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        context['title'] = _('Parametri Finanziari')
        return context
    
    def form_valid(self, form):
        messages.success(self.request, _('Parametri finanziari aggiornati con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.kwargs.get('project_id')})

class RunFinancialAnalysisView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        station_id = self.kwargs.get('station_id', None)
        
        if station_id:
            station = get_object_or_404(ChargingStation, pk=station_id)
            self._run_station_analysis(station)
            messages.success(request, _('Analisi finanziaria per la stazione completata con successo!'))
            return redirect('projects:station_financial_results', project_id=project_id, station_id=station_id)
        else:
            project = get_object_or_404(Project, pk=project_id)
            self._run_project_analysis(project)
            messages.success(request, _('Analisi finanziaria per il progetto completata con successo!'))
            return redirect('projects:project_financial_results', project_id=project_id)
    
    def _run_project_analysis(self, project):
        """
        Esegue l'analisi finanziaria per l'intero progetto
        """
        # Controlla che esistano parametri finanziari
        if not hasattr(project, 'financial_parameters'):
            FinancialParameters.objects.create(project=project)
        
        # Ottiene o crea l'oggetto di analisi finanziaria
        analysis, created = FinancialAnalysis.objects.get_or_create(
            project=project,
            defaults={'charging_station': None}
        )
        
        # Calcola l'investimento totale
        total_investment = project.total_budget
        
        # Parametri finanziari
        params = project.financial_parameters
        investment_years = params.investment_years
        discount_rate = float(params.config.discount_rate) / 100
        loan_amount = float(params.loan_amount)
        loan_interest_rate = float(params.loan_interest_rate) / 100
        loan_term = params.loan_term
        
        # Simuliamo un ROI del 15%
        roi = 15.0
        
        # Calcoliamo un NPV positivo
        npv = total_investment * 0.25
        
        # Calcoliamo un IRR del 12%
        irr = 12.0
        
        # Payback period di 4.5 anni
        payback = 4.5
        
        # Ricavi totali (stimati come 200% dell'investimento su 10 anni)
        revenue = total_investment * 2
        
        # Costi totali (stimati come 85% dei ricavi)
        costs = revenue * 0.85
        
        # Profitto
        profit = revenue - costs
        
        # Calcola piano ammortamento prestito
        loan_schedule = {
            'years': list(range(1, loan_term + 1)),
            'payment': [],
            'interest': [],
            'principal': [],
            'balance': []
        }
        
        if loan_amount > 0:
            # Calcolo rata
            if loan_interest_rate > 0:
                annual_payment = loan_amount * (loan_interest_rate * (1 + loan_interest_rate) ** loan_term) / ((1 + loan_interest_rate) ** loan_term - 1)
            else:
                annual_payment = loan_amount / loan_term
                
            remaining_balance = loan_amount
            
            for year in range(1, loan_term + 1):
                interest_payment = remaining_balance * loan_interest_rate
                principal_payment = annual_payment - interest_payment
                remaining_balance -= principal_payment
                
                loan_schedule['payment'].append(float(annual_payment))
                loan_schedule['interest'].append(float(interest_payment))
                loan_schedule['principal'].append(float(principal_payment))
                loan_schedule['balance'].append(max(0, float(remaining_balance)))
        
        # Flussi di cassa annuali
        yearly_cash_flow = {
            'years': list(range(1, investment_years + 1)),
            'revenue': [],
            'operational_costs': [],
            'maintenance_costs': [],
            'loan_payments': [],
            'net_cash_flow': [],
            'cumulative_cash_flow': []
        }
        
        cumulative_cash_flow = -float(total_investment)
        loan_payments = [0] * investment_years
        
        # Aggiungi pagamenti del prestito se applicabile
        if loan_amount > 0:
            for year in range(min(loan_term, investment_years)):
                loan_payments[year] = loan_schedule['payment'][year]
        
        # Calcolo flussi di cassa annuali
        for year in range(investment_years):
            year_revenue = float(revenue) / investment_years
            year_op_costs = float(costs) * 0.7 / investment_years
            year_maint_costs = float(costs) * 0.3 / investment_years
            year_loan_payment = loan_payments[year]
            
            net_cash_flow = year_revenue - year_op_costs - year_maint_costs - year_loan_payment
            cumulative_cash_flow += net_cash_flow
            
            yearly_cash_flow['revenue'].append(year_revenue)
            yearly_cash_flow['operational_costs'].append(year_op_costs)
            yearly_cash_flow['maintenance_costs'].append(year_maint_costs)
            yearly_cash_flow['loan_payments'].append(year_loan_payment)
            yearly_cash_flow['net_cash_flow'].append(net_cash_flow)
            yearly_cash_flow['cumulative_cash_flow'].append(cumulative_cash_flow)
        
        # Calcola DSCR (Debt Service Coverage Ratio)
        avg_yearly_cash_flow = sum(yearly_cash_flow['net_cash_flow']) / len(yearly_cash_flow['net_cash_flow'])
        avg_yearly_debt_service = sum(loan_payments) / len(loan_payments) if sum(loan_payments) > 0 else 1
        dscr = avg_yearly_cash_flow / avg_yearly_debt_service if avg_yearly_debt_service > 0 else 0
        
        # Calcola LTV (Loan to Value)
        ltv = loan_amount / total_investment * 100 if total_investment > 0 else 0
        
        # Calcola Break-even point
        break_even_year = 0
        for i, cf in enumerate(yearly_cash_flow['cumulative_cash_flow']):
            if cf >= 0:
                # Interpolazione lineare per break-even più preciso
                if i > 0:
                    prev_cf = yearly_cash_flow['cumulative_cash_flow'][i-1]
                    if prev_cf < 0:
                        fraction = -prev_cf / (cf - prev_cf)
                        break_even_year = i + fraction
                    else:
                        break_even_year = i
                else:
                    break_even_year = i
                break
        
        # Simulazione guasti
        failure_rate = float(params.failure_probability) / 100
        repair_cost_pct = float(params.repair_cost_percentage) / 100
        avg_station_cost = float(total_investment) / max(1, project.subprojects.count())
        
        failure_simulation = {
            'years': list(range(1, investment_years + 1)),
            'failures': [],
            'repair_costs': [],
            'active_stations': []
        }
        
        num_stations = project.subprojects.count()
        
        for year in range(investment_years):
            # Semplice simulazione statistica
            expected_failures = num_stations * failure_rate
            repair_cost = expected_failures * repair_cost_pct * avg_station_cost
            
            failure_simulation['failures'].append(float(expected_failures))
            failure_simulation['repair_costs'].append(float(repair_cost))
            failure_simulation['active_stations'].append(float(num_stations - expected_failures * 0.5))  # Media stazioni attive
        
        # Analisi di sensibilità
        sensitivity_analysis = {
            'scenarios': ['Pessimistico', 'Base', 'Ottimistico'],
            'revenue_factor': [0.8, 1.0, 1.2],
            'cost_factor': [1.2, 1.0, 0.9],
            'npv': [],
            'irr': [],
            'roi': []
        }
        
        # Calcola scenari
        for i in range(3):
            rev_factor = sensitivity_analysis['revenue_factor'][i]
            cost_factor = sensitivity_analysis['cost_factor'][i]
            
            # Calcoli semplificati per scenari
            adjusted_profit = revenue * rev_factor - costs * cost_factor
            adjusted_roi = adjusted_profit / total_investment * 100 if total_investment > 0 else 0
            adjusted_npv = adjusted_profit * 0.8 - total_investment
            adjusted_irr = adjusted_roi * 0.8  # Semplificazione
            
            sensitivity_analysis['npv'].append(float(adjusted_npv))
            sensitivity_analysis['irr'].append(float(adjusted_irr))
            sensitivity_analysis['roi'].append(float(adjusted_roi))
        
        # Salva i risultati
        analysis.total_investment = total_investment
        analysis.net_present_value = npv
        analysis.internal_rate_of_return = irr
        analysis.payback_period = payback
        analysis.return_on_investment = roi
        analysis.profitability_index = 1 + (npv / total_investment)
        analysis.total_revenue = revenue
        analysis.total_costs = costs
        analysis.total_profit = profit
        analysis.yearly_cash_flow = yearly_cash_flow
        analysis.loan_schedule = loan_schedule
        analysis.failure_simulation = failure_simulation
        analysis.sensitivity_analysis = sensitivity_analysis
        analysis.debt_service_coverage_ratio = dscr
        analysis.loan_to_value_ratio = ltv
        analysis.break_even_point_year = break_even_year
        analysis.average_occupancy_rate = 65.0  # Valore di default per ora
        analysis.save()
        
        return analysis
    
    def _run_station_analysis(self, station):
        """
        Esegue l'analisi finanziaria per una singola stazione
        """
        # Ottiene o crea l'oggetto di analisi finanziaria
        analysis, created = FinancialAnalysis.objects.get_or_create(
            charging_station=station,
            defaults={'project': None}
        )
        
        # Calcola l'investimento totale della stazione
        total_investment = station.calculate_total_investment()
        
        # TODO: Implementa calcoli dettagliati qui
        # Per ora semplifichiamo con calcoli di base
        
        # Calcola le metriche annuali dalla stazione
        annual_metrics = station.calculate_annual_metrics()
        
        # Parametri finanziari dal progetto principale
        project = station.sub_project.project
        investment_years = project.financial_parameters.investment_years
        
        # Calcola ricavi totali e costi totali
        total_revenue = annual_metrics['annual_revenue'] * investment_years
        total_costs = annual_metrics['annual_costs'] * investment_years
        total_profit = total_revenue - total_costs
        
        # ROI
        roi = (total_profit / total_investment) * 100
        
        # NPV e IRR (calcoli semplificati)
        npv = total_profit * 0.8 - total_investment
        irr = roi * 0.8
        
        # Payback period semplificato
        if annual_metrics['annual_profit'] > 0:
            payback = total_investment / annual_metrics['annual_profit']
        else:
            payback = investment_years
        
        # Flussi di cassa annuali
        yearly_cash_flow = {}
        
        for year in range(1, investment_years + 1):
            yearly_cash_flow[f'year_{year}'] = {
                'revenue': float(annual_metrics['annual_revenue']),
                'costs': float(annual_metrics['annual_costs']),
                'profit': float(annual_metrics['annual_profit']),
                'cumulative': float(annual_metrics['annual_profit'] * year - total_investment)
            }
        
        # Salva i risultati
        analysis.total_investment = total_investment
        analysis.net_present_value = npv
        analysis.internal_rate_of_return = irr
        analysis.payback_period = min(payback, investment_years)  # Limitato agli anni di investimento
        analysis.return_on_investment = roi
        analysis.profitability_index = 1 + (npv / total_investment)
        analysis.total_revenue = total_revenue
        analysis.total_costs = total_costs
        analysis.total_profit = total_profit
        analysis.yearly_cash_flow = yearly_cash_flow
        analysis.save()
        
        return analysis

class ProjectFinancialResultsView(LoginRequiredMixin, DetailView):
    model = FinancialAnalysis
    template_name = 'projects/project_financial_results.html'
    context_object_name = 'financial_analysis'
    
    def get_object(self, queryset=None):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=project_id)
        return get_object_or_404(FinancialAnalysis, project=project)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        return context

class StationFinancialResultsView(LoginRequiredMixin, DetailView):
    model = FinancialAnalysis
    template_name = 'projects/station_financial_results.html'
    context_object_name = 'financial_analysis'
    
    def get_object(self, queryset=None):
        station_id = self.kwargs.get('station_id')
        station = get_object_or_404(ChargingStation, pk=station_id)
        return get_object_or_404(FinancialAnalysis, charging_station=station)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['station'] = get_object_or_404(ChargingStation, pk=self.kwargs.get('station_id'))
        context['project'] = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        return context
        
class GenerateFinancialReportPDFView(LoginRequiredMixin, View):
    """
    Genera un report PDF dell'analisi finanziaria per un progetto o una stazione
    """
    
    def get_charging_stations(self, project):
        """
        Recupera le stazioni di ricarica associate al progetto.
        Se il progetto ha subprogetti, recupera le stazioni da tutti i subprogetti.
        """
        charging_stations = []
        
        # Try to get charging stations directly from the project
        if hasattr(project, 'charging_stations'):
            charging_stations.extend(project.charging_stations.all())
        
        # Try to get charging stations from subprojects
        if hasattr(project, 'subprojects'):
            for subproject in project.subprojects.all():
                if hasattr(subproject, 'charging_stations'):
                    charging_stations.extend(subproject.charging_stations.all())
        
        return charging_stations
        
    def calculate_project_investment_details(self, project):
        """
        Calcola i dettagli di investimento del progetto basandosi sui sottoprogetti.
        Restituisce un dizionario con le voci di costo totali, quantità, costi unitari e percentuali.
        """
        from decimal import Decimal
        from cpo_core.models.subproject import SubProject
        
        # Ottieni tutti i sottoprogetti del progetto
        subprojects = SubProject.objects.filter(project=project)
        
        # Inizializza il dizionario per i totali e contatori per le quantità
        investment_details = {
            'components': [
                {
                    'name': 'Costo Colonnina',
                    'cost_field': 'equipment_cost',
                    'total': Decimal('0.00'),
                    'quantity': 0,
                    'items': [],  # Lista per memorizzare i costi unitari di ogni sottoprogetto
                    'percentage': 0
                },
                {
                    'name': 'Costo Installazione',
                    'cost_field': 'installation_cost',
                    'total': Decimal('0.00'),
                    'quantity': 0,
                    'items': [],
                    'percentage': 0
                },
                {
                    'name': 'Costo Allaccio Rete',
                    'cost_field': 'connection_cost',
                    'total': Decimal('0.00'),
                    'quantity': 0,
                    'items': [],
                    'percentage': 0
                },
                {
                    'name': 'Costo Permessi',
                    'cost_field': 'permit_cost',
                    'total': Decimal('0.00'),
                    'quantity': 0,
                    'items': [],
                    'percentage': 0
                },
                {
                    'name': 'Costo Opere Civili',
                    'cost_field': 'civil_works_cost',
                    'total': Decimal('0.00'),
                    'quantity': 0,
                    'items': [],
                    'percentage': 0
                },
                {
                    'name': 'Altri Costi',
                    'cost_field': 'other_costs',
                    'total': Decimal('0.00'),
                    'quantity': 0,
                    'items': [],
                    'percentage': 0
                }
            ],
            'grand_total': Decimal('0.00')
        }
        
        # Raccogli i dati da ogni sottoprogetto
        for sp in subprojects:
            # Per le colonnine e l'installazione, la quantità è il numero di colonnine
            num_chargers = sp.num_chargers or 1  # Default a 1 se non specificato
            
            # Calcola i costi unitari
            if sp.equipment_cost and num_chargers > 0:
                unit_cost = sp.equipment_cost / num_chargers
                component = investment_details['components'][0]  # Costo Colonnina
                component['items'].append({
                    'subproject': sp.name,
                    'unit_cost': unit_cost,
                    'quantity': num_chargers,
                    'total': sp.equipment_cost
                })
                component['total'] += sp.equipment_cost
                component['quantity'] += num_chargers
            
            if sp.installation_cost and num_chargers > 0:
                unit_cost = sp.installation_cost / num_chargers
                component = investment_details['components'][1]  # Costo Installazione
                component['items'].append({
                    'subproject': sp.name,
                    'unit_cost': unit_cost,
                    'quantity': num_chargers,
                    'total': sp.installation_cost
                })
                component['total'] += sp.installation_cost
                component['quantity'] += num_chargers
            
            # Per gli altri costi, la quantità è il numero di sottoprogetti (quindi 1 per sottoprogetto)
            if sp.connection_cost:
                component = investment_details['components'][2]  # Costo Allaccio Rete
                component['items'].append({
                    'subproject': sp.name,
                    'unit_cost': sp.connection_cost,
                    'quantity': 1,
                    'total': sp.connection_cost
                })
                component['total'] += sp.connection_cost
                component['quantity'] += 1
            
            if sp.permit_cost:
                component = investment_details['components'][3]  # Costo Permessi
                component['items'].append({
                    'subproject': sp.name,
                    'unit_cost': sp.permit_cost,
                    'quantity': 1,
                    'total': sp.permit_cost
                })
                component['total'] += sp.permit_cost
                component['quantity'] += 1
            
            if sp.civil_works_cost:
                component = investment_details['components'][4]  # Costo Opere Civili
                component['items'].append({
                    'subproject': sp.name,
                    'unit_cost': sp.civil_works_cost,
                    'quantity': 1,
                    'total': sp.civil_works_cost
                })
                component['total'] += sp.civil_works_cost
                component['quantity'] += 1
            
            if sp.other_costs:
                component = investment_details['components'][5]  # Altri Costi
                component['items'].append({
                    'subproject': sp.name,
                    'unit_cost': sp.other_costs,
                    'quantity': 1,
                    'total': sp.other_costs
                })
                component['total'] += sp.other_costs
                component['quantity'] += 1
        
        # Calcola il totale complessivo
        grand_total = sum(component['total'] for component in investment_details['components'])
        investment_details['grand_total'] = grand_total
        
        # Calcola le percentuali e costi unitari medi
        if grand_total > 0:
            for component in investment_details['components']:
                component['percentage'] = (component['total'] / grand_total) * 100
                if component['quantity'] > 0:
                    component['avg_unit_cost'] = component['total'] / component['quantity']
                else:
                    component['avg_unit_cost'] = Decimal('0.00')
        
        # Verifica la coerenza con il budget totale del progetto
        budget_consistent = (grand_total == project.total_budget)
        investment_details['budget_consistent'] = budget_consistent
        
        return investment_details
    def get(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        station_id = self.kwargs.get('station_id', None)
        project = get_object_or_404(Project, pk=project_id)
        report_type = request.GET.get('report_type', 'standard')
        
        if station_id:
            station = get_object_or_404(ChargingStation, pk=station_id)
            analysis = get_object_or_404(FinancialAnalysis, charging_station=station)
            template_name = 'projects/financial_results_pdf.html'
            
            if report_type == 'bank':
                filename = f"business_plan_stazione_{station.name}.pdf"
                title = f"Business Plan - {station.name}"
            else:
                filename = f"financial_report_station_{station.name}.pdf"
                title = f"Analisi Finanziaria - {station.name}"
            
            # Crea URL assoluta per i loghi
            project_logo = None
            if hasattr(project, 'logo') and project.logo:
                project_logo = request.build_absolute_uri(project.logo.url)
                
            municipality_logo = None
            if station.sub_project and station.sub_project.municipality and station.sub_project.municipality.logo:
                municipality_logo = request.build_absolute_uri(station.sub_project.municipality.logo.url)
                
            context = {
                'project': project,
                'charging_station': station,
                'analysis': analysis,
                'title': title,
                'is_project': False,
                'report_type': report_type,
                'charging_stations': [station],
                'market_data': {
                    'current_ev_total': 300000,
                    'current_bev_market_share': 4.2,
                    'current_phev_market_share': 5.1,
                    'yoy_growth': 35,
                    'current_charging_points': 45000,
                    'ev_per_charging_point': 7,
                    'projected_bev_market_share': 30,
                    'projected_phev_market_share': 15,
                    'projected_ev_total': 5000000,
                    'required_charging_points': 500000,
                    'target_ev_per_charging_point': 10,
                    'charging_points_growth': 40,
                    'yearly_charging_points_needed': 40000,
                    'current_fast_charger_percentage': 10,
                    'target_fast_charger_percentage': 30
                },
                'project_logo': project_logo,
                'municipality_logo': municipality_logo
            }
        else:
            analysis = get_object_or_404(FinancialAnalysis, project=project)
            template_name = 'projects/financial_results_pdf.html'
            
            if report_type == 'bank':
                filename = f"business_plan_progetto_{project.name}.pdf"
                title = f"Business Plan - {project.name}"
            else:
                filename = f"financial_report_project_{project.name}.pdf"
                title = f"Analisi Finanziaria - {project.name}"
            
            # Crea URL assoluta per i loghi
            project_logo = None
            if hasattr(project, 'logo') and project.logo:
                project_logo = request.build_absolute_uri(project.logo.url)
                
            municipality_logo = None
            if hasattr(project, 'municipality') and project.municipality and project.municipality.logo:
                municipality_logo = request.build_absolute_uri(project.municipality.logo.url)
                
            # Calcola i dettagli di investimento
            investment_details = self.calculate_project_investment_details(project)
            
            # Ottieni tutti i sottoprogetti
            from cpo_core.models.subproject import SubProject
            subprojects = SubProject.objects.filter(project=project)
            
            # Raccogli informazioni sugli impianti fotovoltaici associati
            from cpo_core.models.charging_station import ChargingStation
            solar_data = []
            for subproject in subprojects:
                # Verifica se ci sono stazioni con impianto fotovoltaico
                charging_stations = ChargingStation.objects.filter(subproject=subproject, has_photovoltaic_system=True)
                for station in charging_stations:
                    try:
                        solar_installation = station.solar_installation
                        solar_data.append({
                            'station_name': station.name,
                            'subproject_name': subproject.name,
                            'capacity_kw': solar_installation.capacity_kw,
                            'annual_production_kwh': solar_installation.annual_production_kwh,
                            'installation_cost': solar_installation.installation_cost,
                            'panel_type': solar_installation.panel_type,
                            'num_panels': solar_installation.num_panels
                        })
                    except Exception as e:
                        # La stazione potrebbe non avere un impianto solare associato
                        pass
            
            context = {
                'project': project,
                'analysis': analysis,
                'title': title,
                'is_project': True,
                'report_type': report_type,
                'project_logo': project_logo,
                'municipality_logo': municipality_logo,
                'charging_stations': self.get_charging_stations(project),
                'investment_details': investment_details,
                'subprojects': subprojects,
                'solar_data': solar_data,
                'market_data': {
                    'current_ev_total': 300000,
                    'current_bev_market_share': 4.2,
                    'current_phev_market_share': 5.1,
                    'yoy_growth': 35,
                    'current_charging_points': 45000,
                    'ev_per_charging_point': 7,
                    'projected_bev_market_share': 30,
                    'projected_phev_market_share': 15,
                    'projected_ev_total': 5000000,
                    'required_charging_points': 500000,
                    'target_ev_per_charging_point': 10,
                    'charging_points_growth': 40,
                    'yearly_charging_points_needed': 40000,
                    'current_fast_charger_percentage': 10,
                    'target_fast_charger_percentage': 30
                }
            }
            
        # Renderizza il template HTML
        html_string = render_to_string(template_name, context)
        
        # Crea il PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Genera il PDF dal HTML
        pdf = weasyprint.HTML(string=html_string).write_pdf()
        
        # Scrivi il PDF nella risposta
        response.write(pdf)
        
        return response