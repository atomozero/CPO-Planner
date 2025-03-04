# cpo_planner/projects/admin.py
from django.contrib import admin
from .models import (
    Project, SubProject, Municipality, ChargingStation,
    FinancialParameters, FinancialAnalysis, PhotovoltaicSystem,
    ProjectTimeline, StationTimeline, EnergyContract, ProjectEnergyContract,
    FailureSimulation, ProjectDocument, StationDocument
)

class SubProjectInline(admin.TabularInline):
    model = SubProject
    extra = 0

class ChargingStationInline(admin.TabularInline):
    model = ChargingStation
    extra = 0
    fk_name = 'sub_project'

class FinancialParametersInline(admin.StackedInline):
    model = FinancialParameters
    can_delete = False
    verbose_name_plural = 'Parametri Finanziari'

class ProjectDocumentInline(admin.TabularInline):
    model = ProjectDocument
    extra = 0

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'start_date', 'expected_completion_date', 'status')
    list_filter = ('status', 'region')
    search_fields = ('name', 'description')
    inlines = [FinancialParametersInline, SubProjectInline, ProjectDocumentInline]

@admin.register(SubProject)
class SubProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'municipality', 'start_date', 'expected_completion_date', 'status')
    list_filter = ('status', 'project', 'municipality')
    search_fields = ('name', 'description')
    inlines = [ChargingStationInline]

@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'region')
    list_filter = ('province', 'region')
    search_fields = ('name', 'province', 'region')

@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'identifier', 'address', 'power_type', 'total_power', 'status')
    list_filter = ('status', 'power_type', 'sub_project__municipality')
    search_fields = ('name', 'identifier', 'address')

@admin.register(FinancialParameters)
class FinancialParametersAdmin(admin.ModelAdmin):
    list_display = ('project', 'investment_years', 'loan_amount', 'loan_interest_rate')
    list_filter = ('investment_years', 'pre_amortization_years')
    search_fields = ('project__name',)

@admin.register(FinancialAnalysis)
class FinancialAnalysisAdmin(admin.ModelAdmin):
    list_display = ('project', 'charging_station', 'total_investment', 'net_present_value', 'internal_rate_of_return', 'payback_period')
    list_filter = ('created_at',)
    search_fields = ('project__name', 'charging_station__name')

@admin.register(PhotovoltaicSystem)
class PhotovoltaicSystemAdmin(admin.ModelAdmin):
    list_display = ('charging_station', 'capacity', 'panel_type', 'installation_date')
    list_filter = ('panel_type',)
    search_fields = ('charging_station__name',)

@admin.register(ProjectTimeline)
class ProjectTimelineAdmin(admin.ModelAdmin):
    list_display = ('project', 'planning_start', 'installation_end', 'operation_start')
    search_fields = ('project__name',)

@admin.register(StationTimeline)
class StationTimelineAdmin(admin.ModelAdmin):
    list_display = ('charging_station', 'design_start', 'installation_end', 'commissioning_date')
    search_fields = ('charging_station__name',)

@admin.register(EnergyContract)
class EnergyContractAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'tariff_type', 'energy_price_kwh', 'start_date', 'end_date')
    list_filter = ('tariff_type', 'provider')
    search_fields = ('name', 'provider', 'contract_number')

@admin.register(ProjectEnergyContract)
class ProjectEnergyContractAdmin(admin.ModelAdmin):
    list_display = ('project', 'energy_contract', 'start_date', 'end_date')
    list_filter = ('energy_contract',)
    search_fields = ('project__name', 'energy_contract__name')

@admin.register(FailureSimulation)
class FailureSimulationAdmin(admin.ModelAdmin):
    list_display = ('project', 'total_failures', 'total_repair_costs', 'total_revenue_loss')
    search_fields = ('project__name',)

@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'document_type', 'created_at')
    list_filter = ('document_type',)
    search_fields = ('title', 'description', 'project__name')

@admin.register(StationDocument)
class StationDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'charging_station', 'document_type', 'created_at')
    list_filter = ('document_type',)
    search_fields = ('title', 'description', 'charging_station__name')