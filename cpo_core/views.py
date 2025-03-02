# cpo_core/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone

from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from decimal import Decimal
from datetime import datetime, timedelta

from .models import ( Organization, Project, Municipality, SubProject, ChargingStation, 
    FinancialProjection, YearlyProjection, SolarInstallation
)
from .forms import FinancialProjectionForm

from django.http import JsonResponse
import json

@login_required
def financial_overview(request):
    """Vista panoramica finanziaria di tutti i progetti."""
    # Recupera tutti i progetti con proiezioni finanziarie
    projects_with_financials = Project.objects.filter(financial_projection__isnull=False)
    
    # Calcola i KPI finanziari complessivi
    total_investment = projects_with_financials.aggregate(
        total=Sum('financial_projection__total_investment')
    )['total'] or Decimal('0.0')
    
    avg_roi = projects_with_financials.aggregate(
        avg=Avg('financial_projection__roi')
    )['avg'] or Decimal('0.0')
    
    avg_payback = projects_with_financials.aggregate(
        avg=Avg('financial_projection__payback_period')
    )['avg'] or Decimal('0.0')
    
    # Calcola ricavi e costi annuali aggregati per tutti i progetti
    yearly_data = {}
    yearly_projections = YearlyProjection.objects.filter(
        financial_projection__project__in=projects_with_financials
    )
    
    for projection in yearly_projections:
        year = projection.year
        if year not in yearly_data:
            yearly_data[year] = {
                'revenue': Decimal('0.0'),
                'expenses': Decimal('0.0'),
                'profit': Decimal('0.0')
            }
        
        yearly_data[year]['revenue'] += projection.revenue
        yearly_data[year]['expenses'] += projection.operating_expenses
        yearly_data[year]['profit'] += projection.net_profit
    
    # Converte in lista ordinata per i grafici
    yearly_chart_data = [
        {
            'year': year,
            'revenue': float(data['revenue']),
            'expenses': float(data['expenses']),
            'profit': float(data['profit'])
        }
        for year, data in sorted(yearly_data.items())
    ]
    
    # Progetti ordinati per ROI
    top_roi_projects = projects_with_financials.order_by('-financial_projection__roi')[:5]
    
    context = {
        'projects_count': projects_with_financials.count(),
        'total_investment': total_investment,
        'avg_roi': avg_roi,
        'avg_payback': avg_payback,
        'yearly_chart_data': json.dumps(yearly_chart_data),
        'top_roi_projects': top_roi_projects,
    }
    
    return render(request, 'cpo_core/financial_overview.html', context)

@login_required
def project_financial_detail(request, pk):
    """Vista dettagliata delle proiezioni finanziarie di un progetto specifico."""
    project = get_object_or_404(Project, pk=pk)
    
    try:
        financial_projection = FinancialProjection.objects.get(project=project)
        yearly_projections = YearlyProjection.objects.filter(
            financial_projection=financial_projection
        ).order_by('year')
    except FinancialProjection.DoesNotExist:
        financial_projection = None
        yearly_projections = []
    
    # Recupera dati sulle stazioni di ricarica del progetto
    charging_stations = ChargingStation.objects.filter(
        subproject__project=project
    )
    
    # Recupera dati sugli impianti fotovoltaici
    solar_installations = SolarInstallation.objects.filter(project=project)
    
    # Prepara dati per i grafici
    yearly_chart_data = []
    cumulative_profit = 0
    
    for projection in yearly_projections:
        yearly_profit = projection.revenue - projection.operating_expenses
        cumulative_profit += yearly_profit
        
        yearly_chart_data.append({
            'year': projection.year,
            'revenue': float(projection.revenue),
            'expenses': float(projection.operating_expenses),
            'profit': float(yearly_profit),
            'cumulative_profit': float(cumulative_profit),
            'loan_payment': float(projection.loan_payment)
        })
    
    context = {
        'project': project,
        'financial_projection': financial_projection,
        'yearly_projections': yearly_projections,
        'charging_stations': charging_stations,
        'solar_installations': solar_installations,
        'yearly_chart_data': json.dumps(yearly_chart_data),
    }
    
    return render(request, 'cpo_core/project_financial_detail.html', context)

@login_required
def financial_projection_create(request, project_id):
    """Crea una nuova proiezione finanziaria per un progetto."""
    project = get_object_or_404(Project, pk=project_id)
    
    # Verifica se esiste già una proiezione finanziaria
    if hasattr(project, 'financial_projection'):
        messages.warning(request, f"Esiste già una proiezione finanziaria per {project.name}.")
        return redirect('project_financial_detail', pk=project.id)
    
    if request.method == 'POST':
        form = FinancialProjectionForm(request.POST)
        if form.is_valid():
            financial_projection = form.save(commit=False)
            financial_projection.project = project
            financial_projection.save()
            
            # Ricalcola le proiezioni
            financial_projection.calculate_financial_projections()
            financial_projection.save()
            
            messages.success(request, f"Proiezione finanziaria creata per {project.name}.")
            return redirect('project_financial_detail', pk=project.id)
    else:
        # Inizializza con valori predefiniti basati sul progetto
        charging_stations = ChargingStation.objects.filter(subproject__project=project)
        total_cost = sum(station.calculate_total_cost() for station in charging_stations) if charging_stations else 0
        
        initial_data = {
            'total_investment': total_cost,
            'loan_amount': total_cost,
            'expected_roi': 15.0,  # ROI atteso predefinito del 15%
        }
        form = FinancialProjectionForm(initial=initial_data)
    
    context = {
        'form': form,
        'project': project,
    }
    
    return render(request, 'cpo_core/financial_projection_form.html', context)

@login_required
def financial_projection_update(request, pk):
    """Aggiorna una proiezione finanziaria esistente."""
    financial_projection = get_object_or_404(FinancialProjection, pk=pk)
    project = financial_projection.project
    
    if request.method == 'POST':
        form = FinancialProjectionForm(request.POST, instance=financial_projection)
        if form.is_valid():
            financial_projection = form.save()
            
            # Ricalcola le proiezioni
            financial_projection.calculate_financial_projections()
            financial_projection.save()
            
            messages.success(request, f"Proiezione finanziaria aggiornata per {project.name}.")
            return redirect('project_financial_detail', pk=project.id)
    else:
        form = FinancialProjectionForm(instance=financial_projection)
    
    context = {
        'form': form,
        'project': project,
        'financial_projection': financial_projection,
    }
    
    return render(request, 'cpo_core/financial_projection_form.html', context)

@login_required
def roi_calculator(request):
    """Calcolatore ROI interattivo per simulazioni."""
    if request.method == 'POST':
        # Recupera i dati dal form
        data = {
            'charging_stations': int(request.POST.get('charging_stations', 1)),
            'connectors_per_station': int(request.POST.get('connectors_per_station', 2)),
            'power_kw': float(request.POST.get('power_kw', 22)),
            'equipment_cost': float(request.POST.get('equipment_cost', 15000)),
            'installation_cost': float(request.POST.get('installation_cost', 5000)),
            'connection_cost': float(request.POST.get('connection_cost', 3000)),
            'charging_price_kwh': float(request.POST.get('charging_price_kwh', 0.45)),
            'electricity_cost_kwh': float(request.POST.get('electricity_cost_kwh', 0.25)),
            'avg_daily_sessions': float(request.POST.get('avg_daily_sessions', 6)),
            'avg_kwh_per_session': float(request.POST.get('avg_kwh_per_session', 20)),
            'yearly_maintenance': float(request.POST.get('yearly_maintenance', 1000)),
            'include_solar': request.POST.get('include_solar') == 'on',
            'solar_kwp': float(request.POST.get('solar_kwp', 10)),
            'solar_cost_per_kwp': float(request.POST.get('solar_cost_per_kwp', 1500)),
            'project_years': int(request.POST.get('project_years', 10)),
        }
        
        # Calcola parametri finanziari
        results = calculate_roi_projection(data)
        
        # Se è una richiesta AJAX, restituisci i dati in formato JSON
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(results)
        
        # Altrimenti, passa i risultati alla vista
        context = {
            'form_data': data,
            'results': results,
        }
        
        return render(request, 'cpo_core/roi_calculator.html', context)
    
    # Valori predefiniti per il form
    context = {
        'form_data': {
            'charging_stations': 1,
            'connectors_per_station': 2,
            'power_kw': 22,
            'equipment_cost': 15000,
            'installation_cost': 5000,
            'connection_cost': 3000,
            'charging_price_kwh': 0.45,
            'electricity_cost_kwh': 0.25,
            'avg_daily_sessions': 6,
            'avg_kwh_per_session': 20,
            'yearly_maintenance': 1000,
            'include_solar': False,
            'solar_kwp': 10,
            'solar_cost_per_kwp': 1500,
            'project_years': 10,
        }
    }
    
    return render(request, 'cpo_core/roi_calculator.html', context)

def calculate_roi_projection(data):
    """Calcola le proiezioni ROI basate sui parametri forniti."""
    # Calcolo investimento iniziale
    equipment_cost = data['charging_stations'] * data['equipment_cost']
    installation_cost = data['charging_stations'] * data['installation_cost']
    connection_cost = data['charging_stations'] * data['connection_cost']
    
    # Costo aggiuntivo per impianto fotovoltaico
    solar_cost = data['solar_kwp'] * data['solar_cost_per_kwp'] if data['include_solar'] else 0
    
    # Investimento totale
    total_investment = equipment_cost + installation_cost + connection_cost + solar_cost
    
    # Calcoli per ogni anno
    yearly_projections = []
    cumulative_cash_flow = -total_investment  # Inizia con l'investimento negativo
    total_profit = 0
    payback_year = None
    
    for year in range(1, data['project_years'] + 1):
        # Fattore di crescita dell'utilizzo basato sull'anno (crescita graduale fino al 100%)
        usage_factor = min(1.0, 0.4 + (year - 1) * 0.15)
        
        # Calcolo entrate
        daily_sessions = data['charging_stations'] * data['connectors_per_station'] * data['avg_daily_sessions'] * usage_factor
        annual_kwh = daily_sessions * data['avg_kwh_per_session'] * 365
        annual_revenue = annual_kwh * data['charging_price_kwh']
        
        # Calcolo uscite
        maintenance_factor = 1 + (year - 1) * 0.05  # +5% all'anno
        annual_maintenance = data['charging_stations'] * data['yearly_maintenance'] * maintenance_factor
        
        # Risparmio energia con fotovoltaico (se incluso)
        solar_savings = 0
        if data['include_solar']:
            # Stima produzione annuale: 1300 kWh per kWp installato (media italiana)
            annual_solar_production = data['solar_kwp'] * 1300
            # Applica un fattore di autoconsumo (70% utilizzato direttamente)
            self_consumption_factor = 0.7
            # Risparmio = energia autoconsumata * costo energia
            solar_savings = annual_solar_production * self_consumption_factor * data['electricity_cost_kwh']
        
        # Costo elettricità (sottraendo il risparmio solare)
        annual_electricity_cost = max(0, annual_kwh * data['electricity_cost_kwh'] - solar_savings)
        
        # Calcolo profitto
        annual_expenses = annual_maintenance + annual_electricity_cost
        annual_profit = annual_revenue - annual_expenses
        
        # Aggiornamento flusso di cassa cumulativo
        cumulative_cash_flow += annual_profit
        total_profit += annual_profit
        
        # Determina l'anno di recupero dell'investimento (payback period)
        if payback_year is None and cumulative_cash_flow >= 0:
            # Calcolo preciso con interpolazione lineare
            prev_cash_flow = cumulative_cash_flow - annual_profit
            fraction = abs(prev_cash_flow) / annual_profit
            payback_year = year - 1 + fraction
        
        # Aggiungi dati dell'anno a yearly_projections
        yearly_projections.append({
            'year': year,
            'usage_factor': round(usage_factor * 100, 1),
            'daily_sessions': round(daily_sessions, 1),
            'annual_kwh': round(annual_kwh, 0),
            'revenue': round(annual_revenue, 2),
            'maintenance': round(annual_maintenance, 2),
            'electricity_cost': round(annual_electricity_cost, 2),
            'solar_savings': round(solar_savings, 2),
            'expenses': round(annual_expenses, 2),
            'profit': round(annual_profit, 2),
            'cumulative_cash_flow': round(cumulative_cash_flow, 2)
        })
    
    # Calcola il ROI
    roi = (total_profit / total_investment) * 100 if total_investment > 0 else 0
    
    # Prepara e restituisci i risultati
    results = {
        'total_investment': round(total_investment, 2),
        'equipment_cost': round(equipment_cost, 2),
        'installation_cost': round(installation_cost, 2),
        'connection_cost': round(connection_cost, 2),
        'solar_cost': round(solar_cost, 2),
        'total_profit': round(total_profit, 2),
        'roi': round(roi, 2),
        'payback_year': round(payback_year, 2) if payback_year is not None else None,
        'yearly_projections': yearly_projections
    }
    
    return results

@login_required
def dashboard(request):
    """Dashboard principale dell'applicazione"""
    # Conteggi per la dashboard
    context = {
        'total_projects': Project.objects.count(),
        'active_projects': Project.objects.exclude(status__in=['closed']).count(),
        'total_municipalities': Municipality.objects.count(),
        'total_stations': ChargingStation.objects.count(),
        'operational_stations': ChargingStation.objects.filter(status='operational').count(),
        'projects': Project.objects.order_by('-created_at')[:5],  # Ultimi 5 progetti
        'stations': ChargingStation.objects.order_by('-created_at')[:5],  # Ultime 5 stazioni
    }
    
    # Calcola budget totale e altri dati finanziari
    if Project.objects.exists():
        context['total_budget'] = Project.objects.aggregate(Sum('budget'))['budget__sum']
        
        # Aggiungi ROI medio se esistono proiezioni finanziarie
        avg_roi = FinancialProjection.objects.aggregate(Avg('roi'))['roi__avg']
        if avg_roi:
            context['avg_roi'] = avg_roi
    
    # Dati per grafico stati delle stazioni
    station_status_data = {}
    for status_choice in ChargingStation.STATUS_CHOICES:
        station_status_data[status_choice[1]] = ChargingStation.objects.filter(status=status_choice[0]).count()
    context['station_status_data'] = station_status_data
    
    # Progetti per comune (per grafico)
    projects_by_municipality = Municipality.objects.annotate(
        project_count=Count('subprojects__project', distinct=True)
    ).filter(project_count__gt=0).order_by('-project_count')[:10]
    context['projects_by_municipality'] = projects_by_municipality
    
    # Calcolo previsioni finanziarie mensili (semplificato)
    if context.get('total_budget'):
        today = datetime.now().date()
        monthly_projections = []
        
        for i in range(12):
            month = today + timedelta(days=30 * i)
            monthly_projections.append({
                'month': month,
                'projected_revenue': Decimal(str(float(context['total_budget']) * 0.05 * (i+1) / 12)),
                'projected_costs': Decimal(str(float(context['total_budget']) * 0.02 * (i+1) / 12)),
            })
        
        context['monthly_projections'] = monthly_projections
    
    return render(request, 'cpo_core/dashboard.html', context)

# Viste per Organization
class OrganizationListView(LoginRequiredMixin, ListView):
    model = Organization
    context_object_name = 'organizations'
    template_name = 'core/organization_list.html'

class OrganizationDetailView(LoginRequiredMixin, DetailView):
    model = Organization
    context_object_name = 'organization'
    template_name = 'core/organization_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['projects'] = self.object.projects.all()
        context['total_budget'] = self.object.projects.aggregate(Sum('budget'))['budget__sum'] or 0
        context['total_projects'] = self.object.projects.count()
        return context

class OrganizationCreateView(LoginRequiredMixin, CreateView):
    model = Organization
    fields = ['name', 'tax_id', 'address', 'contact_email', 'contact_phone']
    template_name = 'core/organization_form.html'
    success_url = reverse_lazy('organization_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Organizzazione creata con successo.')
        return super().form_valid(form)

class OrganizationUpdateView(LoginRequiredMixin, UpdateView):
    model = Organization
    fields = ['name', 'tax_id', 'address', 'contact_email', 'contact_phone']
    template_name = 'core/organization_form.html'
    
    def get_success_url(self):
        return reverse_lazy('organization_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Organizzazione aggiornata con successo.')
        return super().form_valid(form)

class OrganizationDeleteView(LoginRequiredMixin, DeleteView):
    model = Organization
    template_name = 'core/organization_confirm_delete.html'
    success_url = reverse_lazy('organization_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Organizzazione eliminata con successo.')
        return super().delete(request, *args, **kwargs)

# Viste per Project
class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'projects'
    template_name = 'core/project_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtra per stato se specificato nella query
        status_filter = self.request.GET.get('status')
        if status_filter:
            context['projects'] = context['projects'].filter(status=status_filter)
            context['current_status'] = dict(Project.STATUS_CHOICES).get(status_filter)
        
        # Aggiungi statistiche
        context['total_projects'] = context['projects'].count()
        context['total_budget'] = context['projects'].aggregate(Sum('budget'))['budget__sum'] or 0
        
        # Aggiungi scelte di stato per i filtri
        context['status_choices'] = Project.STATUS_CHOICES
        return context

class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    context_object_name = 'project'
    template_name = 'core/project_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['subprojects'] = self.object.subprojects.all()
        
        # Calcola il totale delle stazioni di ricarica in questo progetto
        subproject_ids = self.object.subprojects.values_list('id', flat=True)
        context['stations_count'] = ChargingStation.objects.filter(subproject_id__in=subproject_ids).count()
        
        # Ottieni le stazioni operative
        context['operational_stations'] = ChargingStation.objects.filter(
            subproject_id__in=subproject_ids, 
            status='operational'
        ).count()
        
        # Statistiche per comuni e stazioni
        context['municipalities_count'] = self.object.subprojects.values('municipality').distinct().count()
        
        return context

class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    fields = ['name', 'description', 'organization', 'project_manager', 'status', 
              'start_date', 'end_date', 'budget', 'loan_amount', 
              'loan_interest_rate', 'loan_term_years', 'pre_amortization_years']
    template_name = 'core/project_form.html'
    success_url = reverse_lazy('project_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Progetto creato con successo.')
        return super().form_valid(form)

class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = Project
    fields = ['name', 'description', 'organization', 'project_manager', 'status', 
              'start_date', 'end_date', 'budget', 'loan_amount', 
              'loan_interest_rate', 'loan_term_years', 'pre_amortization_years']
    template_name = 'core/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('project_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, 'Progetto aggiornato con successo.')
        return super().form_valid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Progetto eliminato con successo.')
        return super().delete(request, *args, **kwargs)

# Implementa viste simili per Municipality, SubProject, ChargingStation, etc.
# Queste sono le viste di base, le altre seguiranno lo stesso pattern

class MunicipalityListView(LoginRequiredMixin, ListView):
    model = Municipality
    context_object_name = 'municipalities'
    template_name = 'core/municipality_list.html'

class ChargingStationListView(LoginRequiredMixin, ListView):
    model = ChargingStation
    context_object_name = 'stations'
    template_name = 'core/station_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Filtra per tipo o stato se specificato nella query
        type_filter = self.request.GET.get('type')
        status_filter = self.request.GET.get('status')
        
        if type_filter:
            context['stations'] = context['stations'].filter(station_type=type_filter)
            context['current_type'] = dict(ChargingStation.STATION_TYPES).get(type_filter)
            
        if status_filter:
            context['stations'] = context['stations'].filter(status=status_filter)
            context['current_status'] = dict(ChargingStation.STATUS_CHOICES).get(status_filter)
        
        # Aggiungi statistiche
        context['total_stations'] = context['stations'].count()
        context['operational_stations'] = context['stations'].filter(status='operational').count()
        
        # Aggiungi scelte per i filtri
        context['type_choices'] = ChargingStation.STATION_TYPES
        context['status_choices'] = ChargingStation.STATUS_CHOICES
        return context