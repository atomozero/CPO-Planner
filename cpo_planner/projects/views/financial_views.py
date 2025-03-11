# cpo_planner/projects/views/financial_views.py
from django.views.generic import DetailView, CreateView, UpdateView, FormView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from django.utils.translation import gettext_lazy as _

from ..models.project import Project
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
        
        # TODO: Implementa calcoli dettagliati qui
        # Per ora semplifichiamo con calcoli di base
        
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
        
        # Flussi di cassa annuali
        yearly_cash_flow = {}
        investment_years = project.financial_parameters.investment_years
        
        for year in range(1, investment_years + 1):
            yearly_cash_flow[f'year_{year}'] = {
                'revenue': float(revenue / investment_years),
                'costs': float(costs / investment_years),
                'profit': float(profit / investment_years),
                'cumulative': float((profit / investment_years) * year - total_investment)
            }
        
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