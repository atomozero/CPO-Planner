"""Views for the CPO Core app."""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncMonth
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from datetime import datetime, timedelta

from .models.organization import Organization
from .models.project import Project
from infrastructure.models import Municipality
from .models.subproject import SubProject
from .models.charging_station import ChargingStation, SolarInstallation
from .models.financial import FinancialProjection, YearlyProjection
from .forms import FinancialProjectionForm

from django.http import JsonResponse
import json

@login_required
def dashboard(request):
    """Dashboard principale dell'applicazione - versione originale con problemi"""
    # Questa funzione contiene errori e non è in uso
    return render(request, 'cpo_core/dashboard.html', {})

@login_required
def dashboard_simple(request):
    """Dashboard semplificata per risolvere i problemi di login"""
    # Includi i progetti dalle app infrastructure
    # Ora usiamo i modelli consolidati per core e CPO Planner
    from infrastructure.models import ChargingProject, ChargingStation as InfraChargingStation
    
    # Conteggi core projects
    core_projects = Project.objects.all()
    core_projects_count = core_projects.count()
    core_active_projects = core_projects_count  # Tutti attivi per default
    
    # Non abbiamo più un modello separato per cpo_planner
    # Tutto è nel modello Project consolidato
    pl_projects = Project.objects.all()
    pl_projects_count = pl_projects.count()
    pl_active_projects = pl_projects_count  # Tutti attivi per default
    
    # Conteggi infrastructure projects
    infra_projects = ChargingProject.objects.all()
    infra_projects_count = infra_projects.count()
    # ChargingProject ha un campo status e può filtrare correttamente
    infra_active_projects = infra_projects.exclude(status='planning').count()
    
    # Conteggi stazioni - ora ChargingStation è consolidata
    core_stations = ChargingStation.objects.all()
    pl_stations = SubProject.objects.all()  # Collegati a ChargingStation nei template
    infra_stations = InfraChargingStation.objects.all()
    
    # Progetti combinati per la visualizzazione recente (ultimi 5 progetti)
    recent_projects = []
    
    # Aggiungi progetti cpo_planner (stazioni di ricarica)
    for p in pl_projects.order_by('-id')[:5]:
        recent_projects.append({
            'id': p.id,
            'name': p.name,
            'type': 'cpo_planner',
            'created_at': p.start_date if hasattr(p, 'start_date') else datetime.now().date(),
            'status': 'active',  # Valore predefinito poiché il modello Project non ha campo status
            'url': f'/projects/{p.id}/'
        })
    
    # Aggiungi progetti core (convertiti in dizionari)
    for p in core_projects.order_by('-id')[:5]:
        recent_projects.append({
            'id': p.id,
            'name': p.name,
            'type': 'core',
            'created_at': getattr(p, 'created_at', datetime.now().date()),
            'status': 'active',  # Valore predefinito poiché il modello Project non ha campo status
            'url': f'/projects/{p.id}/'
        })
    
    # Aggiungi progetti infrastructure (convertiti in dizionari)
    for p in infra_projects.order_by('-id')[:5]:
        recent_projects.append({
            'id': p.id, 
            'name': p.name,
            'type': 'infrastructure',
            'created_at': p.start_date if hasattr(p, 'start_date') else datetime.now().date(),
            'status': p.status if hasattr(p, 'status') else 'active',
            'url': f'/infrastructure/projects/{p.id}/'
        })
    
    # Ordina tutti i progetti combinati per data (decrescente) se c'è una data
    # Converti tutte le date in str per confronto uniforme
    recent_projects.sort(key=lambda x: str(x.get('created_at') or '2000-01-01'), reverse=True)
    recent_projects = recent_projects[:5]  # Prendi solo i 5 più recenti
    
    # Dati di stato per le stazioni di ricarica
    station_status_data = {
        'Pianificazione': pl_stations.filter(status='planning').count(),
        'In Corso': pl_stations.filter(status__in=['in_progress', 'construction']).count(),
        'Operativo': pl_stations.filter(status='operational').count(),
        'In Manutenzione': pl_stations.filter(status='maintenance').count(),
        'Completato': pl_stations.filter(status='completed').count(),
        'Sospeso': pl_stations.filter(status='suspended').count(),
        'Chiuso': pl_stations.filter(status='closed').count(),
    }
    
    # Calcolo previsioni finanziarie mensili (semplificato)
    # Importiamo il modello Project dalla app projects per usare il campo total_budget
    try:
        from projects.models.project import Project as ProjectsModel
        # Proviamo a calcolare il budget totale usando il modello projects.Project
        projects_ids = [p.id for p in pl_projects]
        projects_with_budget = ProjectsModel.objects.filter(id__in=projects_ids)
        total_budget = projects_with_budget.aggregate(Sum('total_budget'))['total_budget__sum'] or 0
    except (ImportError, Exception) as e:
        # Se c'è un errore, impostiamo un valore predefinito a zero
        print(f"Errore nel recupero del budget totale: {e}")
        total_budget = 0
    
    today = datetime.now().date()
    months = []
    revenues = []
    costs = []
    margins = []
    
    for i in range(12):
        month = today + timedelta(days=30 * i)
        month_name = month.strftime('%b %Y')
        revenue = float(total_budget) * 0.05 * (i+1) / 12
        cost = float(total_budget) * 0.02 * (i+1) / 12
        margin = revenue - cost
        
        months.append(month_name)
        revenues.append(round(revenue, 2))
        costs.append(round(cost, 2))
        margins.append(round(margin, 2))
    
    context = {
        'total_projects': core_projects_count + infra_projects_count + pl_projects_count,
        'active_projects': core_active_projects + infra_active_projects + pl_active_projects,
        'total_municipalities': Municipality.objects.count(),
        'total_stations': core_stations.count() + infra_stations.count() + pl_stations.count(),
        'operational_stations': (
            core_stations.filter(status='operational').count() + 
            infra_stations.filter(status='active').count() +
            pl_stations.filter(status__in=['operational', 'completed']).count()
        ),
        'projects': recent_projects,  # Lista combinata di progetti
        'stations': list(core_stations.order_by('-id')[:5]) + list(pl_stations.order_by('-id')[:5]),  # Ultime stazioni
        'avg_roi': 15.0,  # Valore predefinito
        'station_status_data': station_status_data,
        'months': json.dumps(months),
        'revenues': json.dumps(revenues),
        'costs': json.dumps(costs),
        'margins': json.dumps(margins)
    }
    
    return render(request, 'cpo_core/dashboard.html', context)

class MunicipalityCreateView(CreateView):
    model = Municipality
    fields = ['name', 'province', 'region', 'population']
    template_name = 'municipalities/municipality_form.html'
    success_url = reverse_lazy('municipality_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuovo Comune'
        context['action'] = 'Crea'
        return context

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
        avg=Avg('financial_projection__expected_roi')
    )['avg'] or Decimal('0.0')
    
    avg_payback = projects_with_financials.aggregate(
        avg=Avg('financial_projection__expected_payback_years')
    )['avg'] or Decimal('0.0')
    
    # Calcola ricavi e costi annuali aggregati per tutti i progetti
    yearly_data = {}
    
    # Per evitare errori in caso di tabelle mancanti o modelli non sincronizzati
    try:
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
            
            # Il campo si chiama operational_costs nel modello, non operating_expenses
            expenses = projection.operational_costs
            if hasattr(projection, 'maintenance_costs'):
                expenses += projection.maintenance_costs
            if hasattr(projection, 'electricity_costs'):
                expenses += projection.electricity_costs
                
            yearly_data[year]['expenses'] += expenses
            yearly_data[year]['profit'] += projection.net_profit
    except Exception as e:
        print(f"Errore nel recupero dei dati annuali: {e}")
    
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
    try:
        top_roi_projects = projects_with_financials.order_by('-financial_projection__expected_roi')[:5]
    except Exception as e:
        print(f"Errore nell'ordinamento dei progetti per ROI: {e}")
        top_roi_projects = projects_with_financials[:5]
    
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
        context['status_choices'] = getattr(Project, 'STATUS_CHOICES', [])
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
        # Debug: stampa tutti i dati del form
        print(f"DEBUG: Form data: {form.cleaned_data}")
        
        # Debug: stampa il valore di municipality prima del salvataggio
        municipality = form.cleaned_data.get('municipality')
        print(f"DEBUG: ProjectUpdateView - municipality selezionato: {municipality} (ID: {municipality.id if municipality else 'None'})")
        
        # Salva l'oggetto
        self.object = form.save()
        
        # Debug: stampa l'oggetto dopo il salvataggio
        print(f"DEBUG: Progetto salvato: {self.object}")
        print(f"DEBUG: Municipality dopo salvataggio: {self.object.municipality}")
        
        # Chiama esplicitamente sync_municipalities
        if hasattr(self.object, 'municipality') and self.object.municipality:
            print(f"DEBUG: Sincronizzazione comuni - municipality: {self.object.municipality} (ID: {self.object.municipality.id})")
            if hasattr(self.object, 'sync_municipalities'):
                result = self.object.sync_municipalities()
                print(f"DEBUG: Risultato sincronizzazione: {result}")
        else:
            print("DEBUG: Nessun comune da sincronizzare")
        
        messages.success(self.request, _('Progetto aggiornato con successo!'))
        return super(UpdateView, self).form_valid(form)

class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Progetto eliminato con successo.')
        return super().delete(request, *args, **kwargs)

# Viste per Municipality, SubProject, ChargingStation, etc.
class MunicipalityListView(LoginRequiredMixin, ListView):
    model = Municipality
    context_object_name = 'municipalities'
    template_name = 'core/municipality_list.html'

class ChargingStationDetailView(LoginRequiredMixin, DetailView):
    model = ChargingStation
    context_object_name = 'station'
    template_name = 'cpo_core/chargingstation_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Foto della stazione
        context['station_photos'] = []
        if hasattr(self.object, 'photos'):
            station_photos = self.object.photos.all().order_by('-date_taken', '-created_at')
            context['station_photos'] = station_photos
            
            # Foto divise per fase
            context['pre_installation_photos'] = station_photos.filter(phase='pre_installation')
            context['during_installation_photos'] = station_photos.filter(phase='during_installation')
            context['post_installation_photos'] = station_photos.filter(phase='post_installation')
        
        # Calcoli finanziari dettagliati
        if hasattr(self.object, 'calculate_annual_metrics'):
            context['annual_metrics'] = self.object.calculate_annual_metrics()
        
        # Calcoli giornalieri
        daily_revenue = self.object.charging_price_kwh * self.object.avg_kwh_session * self.object.estimated_sessions_day
        daily_energy_cost = self.object.energy_cost_kwh * self.object.avg_kwh_session * self.object.estimated_sessions_day
        
        context['detailed_calculations'] = {
            'daily_revenue': daily_revenue,
            'annual_revenue': daily_revenue * 365,
            'daily_energy_cost': daily_energy_cost,
            'annual_energy_cost': daily_energy_cost * 365,
            'annual_maintenance_cost': self.object.station_cost * Decimal('0.05'),
            'total_annual_cost': (daily_energy_cost * 365) + (self.object.station_cost * Decimal('0.05')),
            'annual_profit': (daily_revenue * 365) - ((daily_energy_cost * 365) + (self.object.station_cost * Decimal('0.05'))),
        }
        
        return context

@login_required
def charging_station_calculations(request, pk):
    """Vista dettagliata dei calcoli per una stazione di ricarica"""
    station = get_object_or_404(ChargingStation, pk=pk)
    
    # Calcoli utilizzando il metodo standardizzato con gestione errori
    try:
        # Assicuriamo che i campi del subproject siano validi se presente
        if hasattr(station, 'subproject') and station.subproject:
            if station.subproject.local_festival_days is None:
                station.subproject.local_festival_days = 0
                
        annual_revenue = station.calculate_annual_revenue(include_availability=True, include_seasonality=True)
    except Exception as e:
        print(f"DEBUG - Errore nel calcolo ricavi in charging_station_calculations: {e}")
        # Fallback in caso di errore: calcolo più semplice
        daily_revenue = station.charging_price_kwh * station.avg_kwh_session * station.estimated_sessions_day
        annual_revenue = daily_revenue * Decimal('365')
    
    # Calcoli giornalieri
    daily_revenue = station.charging_price_kwh * station.avg_kwh_session * station.estimated_sessions_day
    daily_energy_cost = station.energy_cost_kwh * station.avg_kwh_session * station.estimated_sessions_day
    
    # Costi operativi annuali - assicuriamo coerenza di tipi
    annual_energy_cost = daily_energy_cost * Decimal('365')
    annual_maintenance_cost = station.station_cost * Decimal('0.05')
    total_annual_cost = annual_energy_cost + annual_maintenance_cost
    
    # Conversione esplicita per evitare errori di tipo
    annual_revenue_decimal = Decimal(str(annual_revenue)) if not isinstance(annual_revenue, Decimal) else annual_revenue
    annual_profit = annual_revenue_decimal - total_annual_cost
    
    # Aggiorniamo le metriche annuali con i valori calcolati
    annual_metrics = {
        'annual_revenue': annual_revenue,
        'annual_costs': total_annual_cost,
        'annual_profit': annual_profit
    }
    
    # Calcolo del margine
    margin_per_kwh = station.charging_price_kwh - station.energy_cost_kwh
    margin_percentage = (margin_per_kwh / station.energy_cost_kwh) * Decimal('100') if station.energy_cost_kwh > 0 else Decimal('0')
    
    # Calcolo del ROI con conversione esplicita a Decimal per evitare errori di tipo
    total_investment = station.calculate_total_cost()
    if total_investment > 0:
        # Conversione esplicita a Decimal
        annual_profit_decimal = Decimal(str(annual_profit)) if not isinstance(annual_profit, Decimal) else annual_profit
        total_investment_decimal = Decimal(str(total_investment)) if not isinstance(total_investment, Decimal) else total_investment
        annual_roi = (annual_profit_decimal / total_investment_decimal) * Decimal('100')
    else:
        annual_roi = Decimal('0')
        
    # Calcolo periodo di payback
    if annual_profit > 0:
        annual_profit_decimal = Decimal(str(annual_profit)) if not isinstance(annual_profit, Decimal) else annual_profit
        total_investment_decimal = Decimal(str(total_investment)) if not isinstance(total_investment, Decimal) else total_investment
        payback_years = total_investment_decimal / annual_profit_decimal
    else:
        payback_years = Decimal('0')
    
    # Calcoli per ogni mese (considerando utilizzo stagionale)
    monthly_calculations = []
    monthly_revenue_total = Decimal('0.0')  # Per verifica
    
    for month in range(1, 13):
        # Fattore stagionale: estate (giugno-settembre) ha più utilizzo
        seasonal_factor = Decimal('1.2') if month in [6, 7, 8, 9] else (Decimal('0.8') if month in [12, 1, 2] else Decimal('1.0'))
        
        # Calcoli con fattore stagionale
        monthly_sessions = station.estimated_sessions_day * Decimal('30') * seasonal_factor
        monthly_kwh = monthly_sessions * station.avg_kwh_session
        monthly_revenue = monthly_kwh * station.charging_price_kwh
        monthly_energy_cost = monthly_kwh * station.energy_cost_kwh
        monthly_maintenance_cost = annual_maintenance_cost / Decimal('12')
        monthly_profit = monthly_revenue - (monthly_energy_cost + monthly_maintenance_cost)
        
        # Accumulatore per verifica
        monthly_revenue_total += monthly_revenue
        
        month_name = {
            1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 
            5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
            9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
        }[month]
        
        monthly_calculations.append({
            'month': month,
            'name': month_name,
            'seasonal_factor': seasonal_factor,
            'sessions': monthly_sessions,
            'kwh': monthly_kwh,
            'revenue': monthly_revenue,
            'energy_cost': monthly_energy_cost,
            'maintenance_cost': monthly_maintenance_cost,
            'profit': monthly_profit,
        })
    
    # Applica fattore di disponibilità ai calcoli mensili se ci sono giorni di indisponibilità
    availability_factor = Decimal('1.0')
    unavailable_days = 0
    if hasattr(station, 'subproject') and station.subproject:
        # Assicuriamo che i campi siano validi
        if station.subproject.local_festival_days is None:
            station.subproject.local_festival_days = 0
            
        if station.subproject.weekly_market_day is not None:
            unavailable_days += 52  # 52 settimane
        if station.subproject.local_festival_days:
            unavailable_days += station.subproject.local_festival_days
            
        # Fattore disponibilità
        if unavailable_days > 0:
            total_days = 365
            available_days = total_days - unavailable_days
            # Converte esplicitamente in Decimal usando stringhe per evitare errori di precisione
            availability_factor = Decimal(str(available_days)) / Decimal(str(total_days))
            
            # Aggiorniamo i valori mensili
            for month_calc in monthly_calculations:
                month_calc['revenue'] *= availability_factor
                month_calc['profit'] = month_calc['revenue'] - (month_calc['energy_cost'] + month_calc['maintenance_cost'])
            
            # Aggiorniamo anche il totale per verifica
            monthly_revenue_total *= availability_factor
    
    # Debug per verifica coerenza
    print(f"DEBUG - Controllo coerenza ricavi: annual_revenue={annual_revenue:.2f}, "
          f"totale mensile={monthly_revenue_total:.2f}, differenza={annual_revenue-monthly_revenue_total:.2f}")
    
    context = {
        'station': station,
        'annual_metrics': annual_metrics,
        'daily_revenue': daily_revenue,
        'daily_energy_cost': daily_energy_cost,
        'annual_revenue': annual_revenue,
        'annual_energy_cost': annual_energy_cost,
        'annual_maintenance_cost': annual_maintenance_cost,
        'total_annual_cost': total_annual_cost,
        'annual_profit': annual_profit,
        'margin_per_kwh': margin_per_kwh,
        'margin_percentage': margin_percentage,
        'total_investment': total_investment,
        'annual_roi': annual_roi,
        'payback_years': payback_years,
        'monthly_calculations': monthly_calculations,
        'availability_factor': availability_factor,
    }
    
    return render(request, 'cpo_core/charging_station_calculations.html', context)

@login_required
def charging_station_calculations_subproject(request, subproject_id):
    """Vista dettagliata dei calcoli per un sottoprogetto (che funge da stazione di ricarica)"""
    # Importa il modello SubProject
    from cpo_core.models.subproject import SubProject
    
    # Ottieni il sottoprogetto
    subproject = get_object_or_404(SubProject, pk=subproject_id)
    
    # Cerca se esiste una stazione di ricarica associata a questo subproject
    try:
        station = ChargingStation.objects.get(subproject=subproject)
        # Se esiste, usa la vista esistente
        return charging_station_calculations(request, station.pk)
    except ChargingStation.DoesNotExist:
        # Altrimenti, crea una stazione temporanea in memoria con i dati del subproject
        station = ChargingStation(
            name=subproject.name,
            identifier=f"SUB-{subproject.id}",
            station_type="ac_fast",       # valore predefinito
            power_type="ac",              # valore predefinito
            power_kw=subproject.power_kw or Decimal("22.0"),
            station_cost=subproject.equipment_cost or Decimal("0"),
            installation_cost=subproject.installation_cost or Decimal("0"),
            connection_cost=subproject.connection_cost or Decimal("0"),
            energy_cost_kwh=Decimal("0.25"),      # valore predefinito
            charging_price_kwh=Decimal("0.45"),   # valore predefinito
            estimated_sessions_day=Decimal("5.0"), # valore predefinito 
            avg_kwh_session=Decimal("15.0")       # valore predefinito
        )
        
        # Associa il subproject alla stazione temporanea per i calcoli di disponibilità
        station.subproject = subproject
        
        # Assicuriamo che i campi del subproject siano validi
        if subproject.local_festival_days is None:
            subproject.local_festival_days = 0
        
        # Calcola i ricavi usando il metodo standardizzato con gestione degli errori
        try:
            annual_revenue = station.calculate_annual_revenue(
                include_availability=True,
                include_seasonality=True
            )
        except Exception as e:
            print(f"DEBUG - Errore nel calcolo ricavi in charging_station_calculations_subproject: {e}")
            # Fallback in caso di errore: calcolo più semplice
            daily_revenue = station.charging_price_kwh * station.avg_kwh_session * station.estimated_sessions_day
            annual_revenue = daily_revenue * Decimal('365')
        
        # Calcoli giornalieri
        daily_revenue = station.charging_price_kwh * station.avg_kwh_session * station.estimated_sessions_day
        daily_energy_cost = station.energy_cost_kwh * station.avg_kwh_session * station.estimated_sessions_day
        
        # Costi operativi annuali - assicuriamo coerenza di tipi
        annual_energy_cost = daily_energy_cost * Decimal('365')
        annual_maintenance_cost = station.station_cost * Decimal('0.05')
        total_annual_cost = annual_energy_cost + annual_maintenance_cost
        
        # Conversione esplicita per evitare errori di tipo
        annual_revenue_decimal = Decimal(str(annual_revenue)) if not isinstance(annual_revenue, Decimal) else annual_revenue
        annual_profit = annual_revenue_decimal - total_annual_cost
        
        # Calcolo del margine
        margin_per_kwh = station.charging_price_kwh - station.energy_cost_kwh
        margin_percentage = (margin_per_kwh / station.energy_cost_kwh) * Decimal('100') if station.energy_cost_kwh > 0 else Decimal('0')
        
        # Calcolo del ROI con conversione esplicita a Decimal per evitare errori di tipo
        total_investment = station.calculate_total_cost()
        if total_investment > 0:
            # Conversione esplicita a Decimal
            annual_profit_decimal = Decimal(str(annual_profit)) if not isinstance(annual_profit, Decimal) else annual_profit
            total_investment_decimal = Decimal(str(total_investment)) if not isinstance(total_investment, Decimal) else total_investment
            annual_roi = (annual_profit_decimal / total_investment_decimal) * Decimal('100')
        else:
            annual_roi = Decimal('0')
            
        # Calcolo periodo di payback
        if annual_profit > 0:
            annual_profit_decimal = Decimal(str(annual_profit)) if not isinstance(annual_profit, Decimal) else annual_profit
            total_investment_decimal = Decimal(str(total_investment)) if not isinstance(total_investment, Decimal) else total_investment
            payback_years = total_investment_decimal / annual_profit_decimal
        else:
            payback_years = Decimal('0')
        
        # Calcoli per ogni mese (considerando utilizzo stagionale)
        monthly_calculations = []
        monthly_revenue_total = Decimal('0.0')  # Per verifica
        
        for month in range(1, 13):
            # Fattore stagionale: estate (giugno-settembre) ha più utilizzo
            seasonal_factor = Decimal('1.2') if month in [6, 7, 8, 9] else (Decimal('0.8') if month in [12, 1, 2] else Decimal('1.0'))
            
            # Calcoli con fattore stagionale
            monthly_sessions = station.estimated_sessions_day * Decimal('30') * seasonal_factor
            monthly_kwh = monthly_sessions * station.avg_kwh_session
            monthly_revenue = monthly_kwh * station.charging_price_kwh
            monthly_energy_cost = monthly_kwh * station.energy_cost_kwh
            monthly_maintenance_cost = annual_maintenance_cost / Decimal('12')
            monthly_profit = monthly_revenue - (monthly_energy_cost + monthly_maintenance_cost)
            
            # Accumulatore per verifica
            monthly_revenue_total += monthly_revenue
            
            month_name = {
                1: 'Gennaio', 2: 'Febbraio', 3: 'Marzo', 4: 'Aprile', 
                5: 'Maggio', 6: 'Giugno', 7: 'Luglio', 8: 'Agosto',
                9: 'Settembre', 10: 'Ottobre', 11: 'Novembre', 12: 'Dicembre'
            }[month]
            
            monthly_calculations.append({
                'month': month,
                'name': month_name,
                'seasonal_factor': seasonal_factor,
                'sessions': monthly_sessions,
                'kwh': monthly_kwh,
                'revenue': monthly_revenue,
                'energy_cost': monthly_energy_cost,
                'maintenance_cost': monthly_maintenance_cost,
                'profit': monthly_profit,
            })
        
        # Applica fattore di disponibilità ai calcoli mensili se ci sono giorni di indisponibilità
        availability_factor = Decimal('1.0')
        unavailable_days = 0
        
        if subproject.weekly_market_day is not None:
            unavailable_days += 52  # 52 settimane
        if subproject.local_festival_days:
            unavailable_days += subproject.local_festival_days
            
        # Fattore disponibilità
        if unavailable_days > 0:
            total_days = 365
            available_days = total_days - unavailable_days
            # Converte esplicitamente in Decimal usando stringhe per evitare errori di precisione
            availability_factor = Decimal(str(available_days)) / Decimal(str(total_days))
            
            # Aggiorniamo i valori mensili
            for month_calc in monthly_calculations:
                month_calc['revenue'] *= availability_factor
                month_calc['profit'] = month_calc['revenue'] - (month_calc['energy_cost'] + month_calc['maintenance_cost'])
            
            # Aggiorniamo anche il totale per verifica
            monthly_revenue_total *= availability_factor
        
        # Debug per verifica coerenza
        print(f"DEBUG - SubProject {subproject_id} - Controllo coerenza ricavi: annual_revenue={annual_revenue:.2f}, "
              f"totale mensile={monthly_revenue_total:.2f}, differenza={annual_revenue-monthly_revenue_total:.2f}")
        
        # Metriche annuali per il template
        annual_metrics = {
            'annual_revenue': annual_revenue,
            'annual_costs': total_annual_cost,
            'annual_profit': annual_profit
        }
            
        context = {
            'station': station,
            'subproject': subproject,  # Passiamo anche il subproject per riferimento
            'annual_metrics': annual_metrics,
            'daily_revenue': daily_revenue,
            'daily_energy_cost': daily_energy_cost,
            'annual_revenue': annual_revenue,
            'annual_energy_cost': annual_energy_cost,
            'annual_maintenance_cost': annual_maintenance_cost,
            'total_annual_cost': total_annual_cost,
            'annual_profit': annual_profit,
            'margin_per_kwh': margin_per_kwh,
            'margin_percentage': margin_percentage,
            'total_investment': total_investment,
            'annual_roi': annual_roi,
            'payback_years': payback_years,
            'monthly_calculations': monthly_calculations,
            'availability_factor': availability_factor,
            'unavailable_days': unavailable_days,
        }
        
        return render(request, 'cpo_core/charging_station_calculations.html', context)

class ChargingStationListView(LoginRequiredMixin, ListView):
    model = ChargingStation
    context_object_name = 'stations'
    template_name = 'cpo_core/chargingstation_list.html'
    
    def get_queryset(self):
        """
        Override per includere i dati da più fonti
        """
        from cpo_core.models.subproject import SubProject
        
        # Crea una lista di oggetti "simili a stazioni" da diverse fonti
        combined_stations = []
        
        # 1. Aggiungi le stazioni dal modello ChargingStation
        core_stations = ChargingStation.objects.all()
        for station in core_stations:
            combined_stations.append({
                'id': f"cs-{station.id}",
                'name': station.name,
                'code': station.identifier,
                'address': station.address,
                'power_kw': station.power_kw or 22,
                'status': station.status,
                'latitude': station.latitude,
                'longitude': station.longitude,
                'connector_types': station.connector_types,
                'num_connectors': station.num_connectors,
                'municipality_name': station.subproject.municipality.name if hasattr(station, 'subproject') and station.subproject else "Milano",
                'project_name': station.subproject.project.name if hasattr(station, 'subproject') and station.subproject else "Progetto CPO",
                'source': 'core'
            })
            
        # 2. Aggiungi i subprojects come stazioni
        subprojects = SubProject.objects.all()
        for sp in subprojects:
            combined_stations.append({
                'id': f"sp-{sp.id}",
                'name': sp.name,
                'code': f"SP-{sp.id}",
                'address': sp.address or "Via Roma, 1",
                'power_kw': sp.power_kw or 22,
                'status': sp.status,
                'latitude': sp.latitude_approved or sp.latitude_proposed,
                'longitude': sp.longitude_approved or sp.longitude_proposed,
                'connector_types': sp.connector_types or "Type 2, CCS",
                'num_connectors': sp.num_connectors or 2,
                'municipality_name': sp.municipality.name if sp.municipality else "Milano",
                'project_name': sp.project.name if sp.project else "Progetto CPO",
                'source': 'subproject'
            })
            
        # 3. Se necessario, aggiungi anche le stazioni da infrastructure
        try:
            from infrastructure.models import ChargingStation as InfraStation
            infra_stations = InfraStation.objects.all()
            for station in infra_stations:
                combined_stations.append({
                    'id': f"infra-{station.id}",
                    'name': station.name,
                    'code': station.identifier if hasattr(station, 'identifier') else f"IS-{station.id}",
                    'address': station.address or "Via Roma, 1",
                    'power_kw': station.power_kw or 22,
                    'status': station.status,
                    'latitude': station.latitude if hasattr(station, 'latitude') else None,
                    'longitude': station.longitude if hasattr(station, 'longitude') else None,
                    'connector_types': station.connector_types if hasattr(station, 'connector_types') else "Type 2",
                    'num_connectors': station.connector_count if hasattr(station, 'connector_count') else 2,
                    'municipality_name': station.municipality.name if hasattr(station, 'municipality') and station.municipality else "Milano",
                    'project_name': station.project.name if hasattr(station, 'project') and station.project else "Progetto Infrastruttura",
                    'source': 'infrastructure'
                })
        except (ImportError, AttributeError):
            # Se il modello non esiste o ha un'altra struttura, ignoriamo
            pass
            
        return combined_stations
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        stations = context['stations']
        
        # Aggiornamento delle statistiche
        context['total_stations'] = len(stations)
        context['active_stations'] = sum(1 for s in stations if s['status'] in ['active', 'operational'])
        
        # Calcola la potenza totale
        context['total_power'] = sum(float(s['power_kw'] or 0) for s in stations)
        
        # Calcola i progetti unici
        unique_projects = set(s['project_name'] for s in stations if s['project_name'])
        context['total_projects'] = len(unique_projects)
        
        # Distribuzioni di stato per i grafici
        status_choices = [
            ('planned', 'Pianificata'),
            ('installing', 'In Installazione'),
            ('active', 'Attiva'),
            ('operational', 'Operativa'),
            ('maintenance', 'In Manutenzione'),
            ('inactive', 'Inattiva')
        ]
        
        status_counts = {}
        for status_code, status_name in status_choices:
            status_counts[status_code] = sum(1 for s in stations if s['status'] == status_code)
        context['status_counts'] = status_counts
        
        # Distribuzioni di potenza per i grafici
        power_ranges = [
            {'min': 0, 'max': 22, 'range': '0-22 kW'},
            {'min': 22, 'max': 50, 'range': '22-50 kW'},
            {'min': 50, 'max': 100, 'range': '50-100 kW'},
            {'min': 100, 'max': 150, 'range': '100-150 kW'},
            {'min': 150, 'max': 350, 'range': '150-350 kW'},
            {'min': 350, 'max': 9999, 'range': '>350 kW'},
        ]
        
        power_distribution = []
        for power_range in power_ranges:
            if power_range['min'] == 0:
                count = sum(1 for s in stations if float(s['power_kw'] or 0) <= power_range['max'])
            elif power_range['max'] == 9999:
                count = sum(1 for s in stations if float(s['power_kw'] or 0) > power_range['min'])
            else:
                count = sum(1 for s in stations if power_range['min'] < float(s['power_kw'] or 0) <= power_range['max'])
            power_distribution.append({'range': power_range['range'], 'count': count})
        
        context['power_distribution'] = power_distribution
        
        # Stazioni con coordinate per la mappa
        context['stations_with_coords'] = [s for s in stations if s['latitude'] and s['longitude']]
        
        return context