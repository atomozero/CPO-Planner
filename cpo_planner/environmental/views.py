# environmental/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum, Avg, Count, Q
from django.contrib.contenttypes.models import ContentType
import json

from cpo_planner.projects.models import Project, SubProject, ChargingStation
from .models import (
    EmissionFactor, VehicleType, EnvironmentalAnalysis, YearlyEnvironmentalData
)
from .forms import (
    EmissionFactorForm, VehicleTypeForm, EnvironmentalAnalysisForm, EnvironmentalAnalysisFilterForm
)
from .services import EnvironmentalCalculator

class EnvironmentalDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard ambientale"""
    template_name = 'environmental/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiche generali
        context['total_analyses'] = EnvironmentalAnalysis.objects.count()
        context['total_emission_factors'] = EmissionFactor.objects.count()
        context['total_vehicle_types'] = VehicleType.objects.count()
        
        # Ultimi dati
        context['recent_analyses'] = EnvironmentalAnalysis.objects.order_by('-created_at')[:5]
        
        # Impatto totale
        context['total_energy_delivered'] = EnvironmentalAnalysis.objects.aggregate(
            total=Sum('total_energy_delivered')
        )['total'] or 0
        
        context['total_co2_saved'] = EnvironmentalAnalysis.objects.aggregate(
            total=Sum('total_co2_saved')
        )['total'] or 0
        
        # Calcolo alberi equivalenti (1 albero assorbe circa 20kg CO2/anno)
        context['total_trees'] = int(context['total_co2_saved'] * 1000 / 20) if context['total_co2_saved'] else 0
        
        # Dati per il grafico CO2 risparmiata per anno
        yearly_data = YearlyEnvironmentalData.objects.values('year').annotate(
            saved=Sum('co2_saved')
        ).order_by('year')
        
        years = [data['year'] for data in yearly_data]
        saved = [data['saved'] or 0 for data in yearly_data]
        
        # Se non ci sono dati, inizializza con valori vuoti
        if not years:
            current_year = timezone.now().year
            years = list(range(current_year, current_year + 5))
            saved = [0] * len(years)
            
        context['chart_years'] = json.dumps(years)
        context['chart_saved'] = json.dumps(saved)
        
        # Dati per il grafico bilancio emissioni
        total_emissions = EnvironmentalAnalysis.objects.aggregate(
            total=Sum('total_co2_emissions')
        )['total'] or 0
        
        context['emissions_balance'] = {
            'saved': context['total_co2_saved'],
            'emitted': total_emissions
        }
        
        return context

# Viste per EmissionFactor
class EmissionFactorListView(LoginRequiredMixin, ListView):
    """Lista dei fattori di emissione"""
    model = EmissionFactor
    template_name = 'environmental/emission_factor_list.html'
    context_object_name = 'emission_factors'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtra per tipo di fonte
        source_type = self.request.GET.get('source_type')
        if source_type:
            queryset = queryset.filter(source_type=source_type)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['source_types'] = EmissionFactor.EnergySourceType.choices
        return context

class EmissionFactorDetailView(LoginRequiredMixin, DetailView):
    """Dettaglio di un fattore di emissione"""
    model = EmissionFactor
    template_name = 'environmental/emission_factor_detail.html'
    context_object_name = 'emission_factor'

class EmissionFactorCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Creazione di un nuovo fattore di emissione"""
    model = EmissionFactor
    form_class = EmissionFactorForm
    template_name = 'environmental/emission_factor_form.html'
    permission_required = 'environmental.add_emissionfactor'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, _('Fattore di emissione creato con successo.'))
        return reverse('environmental:emission_factor_detail', kwargs={'pk': self.object.pk})

class EmissionFactorUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modifica di un fattore di emissione"""
    model = EmissionFactor
    form_class = EmissionFactorForm
    template_name = 'environmental/emission_factor_form.html'
    permission_required = 'environmental.change_emissionfactor'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context
    
    def get_success_url(self):
        messages.success(self.request, _('Fattore di emissione aggiornato con successo.'))
        return reverse('environmental:emission_factor_detail', kwargs={'pk': self.object.pk})

class EmissionFactorDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminazione di un fattore di emissione"""
    model = EmissionFactor
    template_name = 'environmental/emission_factor_confirm_delete.html'
    permission_required = 'environmental.delete_emissionfactor'
    success_url = reverse_lazy('environmental:emission_factor_list')
    
    def delete(self, request, *args, **kwargs):
        emission_factor = self.get_object()
        
        # Verifica se il fattore è usato in qualche analisi
        if (EnvironmentalAnalysis.objects.filter(electricity_emission_factor=emission_factor).exists() or
            EnvironmentalAnalysis.objects.filter(fuel_emission_factor=emission_factor).exists()):
            messages.error(request, _('Impossibile eliminare il fattore di emissione perché è utilizzato in una o più analisi.'))
            return redirect('environmental:emission_factor_detail', pk=emission_factor.pk)
            
        messages.success(request, _('Fattore di emissione eliminato con successo.'))
        return super().delete(request, *args, **kwargs)

# Viste per VehicleType
class VehicleTypeListView(LoginRequiredMixin, ListView):
    """Lista dei tipi di veicolo"""
    model = VehicleType
    template_name = 'environmental/vehicle_type_list.html'
    context_object_name = 'vehicle_types'
    paginate_by = 10

class VehicleTypeDetailView(LoginRequiredMixin, DetailView):
    """Dettaglio di un tipo di veicolo"""
    model = VehicleType
    template_name = 'environmental/vehicle_type_detail.html'
    context_object_name = 'vehicle_type'

class VehicleTypeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Creazione di un nuovo tipo di veicolo"""
    model = VehicleType
    form_class = VehicleTypeForm
    template_name = 'environmental/vehicle_type_form.html'
    permission_required = 'environmental.add_vehicletype'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_success_url(self):
        messages.success(self.request, _('Tipo di veicolo creato con successo.'))
        return reverse('environmental:vehicle_type_detail', kwargs={'pk': self.object.pk})

class VehicleTypeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Modifica di un tipo di veicolo"""
    model = VehicleType
    form_class = VehicleTypeForm
    template_name = 'environmental/vehicle_type_form.html'
    permission_required = 'environmental.change_vehicletype'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context
    
    def get_success_url(self):
        messages.success(self.request, _('Tipo di veicolo aggiornato con successo.'))
        return reverse('environmental:vehicle_type_detail', kwargs={'pk': self.object.pk})

class VehicleTypeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Eliminazione di un tipo di veicolo"""
    model = VehicleType
    template_name = 'environmental/vehicle_type_confirm_delete.html'
    permission_required = 'environmental.delete_vehicletype'
    success_url = reverse_lazy('environmental:vehicle_type_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Tipo di veicolo eliminato con successo.'))
        return super().delete(request, *args, **kwargs)

# Viste per EnvironmentalAnalysis
class EnvironmentalAnalysisListView(LoginRequiredMixin, ListView):
    """Lista delle analisi ambientali"""
    model = EnvironmentalAnalysis
    template_name = 'environmental/analysis_list.html'
    context_object_name = 'analyses'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtri
        form = EnvironmentalAnalysisFilterForm(self.request.GET)
        if form.is_valid():
            # Ricerca testuale
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) | 
                    Q(description__icontains=search)
                )
                
            # Filtro per tipo di entità
            entity_type = form.cleaned_data.get('entity_type')
            if entity_type:
                if entity_type == 'project':
                    content_type = ContentType.objects.get_for_model(Project)
                    queryset = queryset.filter(content_type=content_type)
                elif entity_type == 'subproject':
                    content_type = ContentType.objects.get_for_model(SubProject)
                    queryset = queryset.filter(content_type=content_type)
                elif entity_type == 'chargingstation':
                    content_type = ContentType.objects.get_for_model(ChargingStation)
                    queryset = queryset.filter(content_type=content_type)
                elif entity_type == 'none':
                    queryset = queryset.filter(content_type__isnull=True)
                    
            # Filtri per data
            date_from = form.cleaned_data.get('date_from')
            if date_from:
                queryset = queryset.filter(created_at__date__gte=date_from)
                
            date_to = form.cleaned_data.get('date_to')
            if date_to:
                queryset = queryset.filter(created_at__date__lte=date_to)
                
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = EnvironmentalAnalysisFilterForm(self.request.GET)
        return context

class EnvironmentalAnalysisDetailView(LoginRequiredMixin, DetailView):
    """Dettaglio di un'analisi ambientale"""
    model = EnvironmentalAnalysis
    template_name = 'environmental/analysis_detail.html'
    context_object_name = 'analysis'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Dati annuali per i grafici
        context['yearly_data'] = self.object.get_yearly_data()
        
        return context

class EnvironmentalAnalysisCreateView(LoginRequiredMixin, CreateView):
    """Creazione di una nuova analisi ambientale"""
    model = EnvironmentalAnalysis
    form_class = EnvironmentalAnalysisForm
    template_name = 'environmental/analysis_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Se è specificata un'entità nella URL
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            if entity_type == 'project':
                context['entity'] = get_object_or_404(Project, id=entity_id)
            elif entity_type == 'subproject':
                context['entity'] = get_object_or_404(SubProject, id=entity_id)
            elif entity_type == 'chargingstation':
                context['entity'] = get_object_or_404(ChargingStation, id=entity_id)
                
            context['entity_type'] = entity_type
            
        return context
    
    def form_valid(self, form):
        # Salva l'analisi
        analysis = form.save()
        
        # Calcola l'impatto ambientale
        success = analysis.calculate()
        
        if success:
            messages.success(self.request, _('Analisi ambientale creata e calcolata con successo.'))
        else:
            messages.warning(self.request, _('Analisi ambientale creata, ma si sono verificati errori durante il calcolo.'))
            
        return redirect('environmental:analysis_detail', pk=analysis.pk)
    
    def get_initial(self):
        initial = super().get_initial()
        
        # Precompila il form se l'entità è specificata nella URL
        entity_type = self.kwargs.get('entity_type')
        entity_id = self.kwargs.get('entity_id')
        
        if entity_type and entity_id:
            initial['entity_type'] = entity_type
            
            if entity_type == 'project':
                initial['project'] = entity_id
            elif entity_type == 'subproject':
                initial['subproject'] = entity_id
            elif entity_type == 'chargingstation':
                initial['chargingstation'] = entity_id
                
        return initial

class EnvironmentalAnalysisUpdateView(LoginRequiredMixin, UpdateView):
    """Modifica di un'analisi ambientale"""
    model = EnvironmentalAnalysis
    form_class = EnvironmentalAnalysisForm
    template_name = 'environmental/analysis_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_update'] = True
        return context
    
    def form_valid(self, form):
        # Salva l'analisi
        analysis = form.save()
        
        # Ricalcola l'impatto ambientale
        success = analysis.calculate()
        
        if success:
            messages.success(self.request, _('Analisi ambientale aggiornata e ricalcolata con successo.'))
        else:
            messages.warning(self.request, _('Analisi ambientale aggiornata, ma si sono verificati errori durante il ricalcolo.'))
            
        return redirect('environmental:analysis_detail', pk=analysis.pk)

class EnvironmentalAnalysisDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminazione di un'analisi ambientale"""
    model = EnvironmentalAnalysis
    template_name = 'environmental/analysis_confirm_delete.html'
    success_url = reverse_lazy('environmental:analysis_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Analisi ambientale eliminata con successo.'))
        return super().delete(request, *args, **kwargs)

class RecalculateAnalysisView(LoginRequiredMixin, UpdateView):
    """Vista per ricalcolare un'analisi ambientale"""
    model = EnvironmentalAnalysis
    http_method_names = ['post']
    
    def post(self, request, *args, **kwargs):
        analysis = self.get_object()
        
        # Ricalcola l'impatto ambientale
        success = analysis.calculate()
        
        if success:
            messages.success(request, _('Analisi ambientale ricalcolata con successo.'))
        else:
            messages.error(request, _('Si sono verificati errori durante il ricalcolo dell\'analisi.'))
            
        return redirect('environmental:analysis_detail', pk=analysis.pk)

def analysis_data_api(request, pk):
    """API per ottenere i dati di un'analisi ambientale per i grafici"""
    try:
        analysis = EnvironmentalAnalysis.objects.get(pk=pk)
        yearly_data = list(analysis.get_yearly_data())
        
        return JsonResponse({
            'success': True,
            'yearly_data': yearly_data,
            'total_energy_delivered': analysis.total_energy_delivered,
            'total_co2_emissions': analysis.total_co2_emissions,
            'total_co2_saved': analysis.total_co2_saved,
            'equivalent_trees': analysis.equivalent_trees,
            'equivalent_ice_km': analysis.equivalent_ice_km
        })
    except EnvironmentalAnalysis.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Analysis not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)