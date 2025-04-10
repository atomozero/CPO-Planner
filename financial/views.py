from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Avg, Count
from django.utils import timezone  # Aggiungi questa importazione

from projects.models import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.charging_station import ChargingStation
from .models import (
    ElectricitySupplyContract, FinancialProjection, 
    YearlyProjection, ChargingStationFinancials,
    StationYearlyProjection, ExitStrategy
)

@login_required
def financial_dashboard(request):
    """Dashboard finanziaria principale"""
    context = {
        'total_projects': Project.objects.count(),
        'total_projections': FinancialProjection.objects.count(),
        'total_contracts': ElectricitySupplyContract.objects.count(),
        'total_exit_strategies': ExitStrategy.objects.count(),
    }
    
    # Somma totale investimenti
    if FinancialProjection.objects.exists():
        context['total_investments'] = FinancialProjection.objects.aggregate(
            Sum('total_investment')
        )['total_investment__sum']
        
        # Media ROI e payback
        context['avg_roi'] = FinancialProjection.objects.aggregate(
            Avg('expected_roi')
        )['expected_roi__avg']
        
        context['avg_payback'] = FinancialProjection.objects.aggregate(
            Avg('expected_payback_years')
        )['expected_payback_years__avg']
    
    # Ottieni le ultime proiezioni finanziarie
    context['recent_projections'] = FinancialProjection.objects.order_by('-created_at')[:5]
    
    # Ottieni i contratti elettrici recenti
    context['recent_contracts'] = ElectricitySupplyContract.objects.order_by('-start_date')[:5]
    
    return render(request, 'financial/dashboard.html', context)

# Qui puoi aggiungere altre viste per le entità finanziarie
# Ad esempio, viste per ElectricitySupplyContract, FinancialProjection, etc.

# Classe di esempio per la lista dei contratti di fornitura elettrica
class ElectricitySupplyContractListView(LoginRequiredMixin, ListView):
    model = ElectricitySupplyContract
    context_object_name = 'contracts'
    template_name = 'financial/contract_list.html'
    
    def get_queryset(self):
        return ElectricitySupplyContract.objects.order_by('-start_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['active_contracts'] = self.get_queryset().filter(
            end_date__gt=timezone.now().date()
        ).count()
        return context