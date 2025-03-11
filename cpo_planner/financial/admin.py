from django.contrib import admin
from .models import (
    ElectricitySupplyContract, FinancialProjection, 
    YearlyProjection, ChargingStationFinancials,
    StationYearlyProjection, ExitStrategy
)

@admin.register(ElectricitySupplyContract)
class ElectricitySupplyContractAdmin(admin.ModelAdmin):
    list_display = ('name', 'provider', 'start_date', 'end_date', 'base_price_per_kwh')
    search_fields = ('name', 'provider')

@admin.register(FinancialProjection)
class FinancialProjectionAdmin(admin.ModelAdmin):
    list_display = ('project', 'total_investment', 'expected_roi', 'expected_payback_years', 'npv', 'irr')
    search_fields = ('project__name',)

class YearlyProjectionInline(admin.TabularInline):
    model = YearlyProjection
    extra = 1

@admin.register(YearlyProjection)
class YearlyProjectionAdmin(admin.ModelAdmin):
    list_display = ('financial_projection', 'year', 'revenue', 'net_profit', 'cash_flow')
    list_filter = ('year',)
    search_fields = ('financial_projection__project__name',)

@admin.register(ChargingStationFinancials)
class ChargingStationFinancialsAdmin(admin.ModelAdmin):
    list_display = ('charging_station', 'charging_price_per_kwh', 'estimated_daily_sessions', 
                    'estimated_annual_revenue', 'estimated_annual_profit', 'estimated_roi_years')
    search_fields = ('charging_station__name',)

class StationYearlyProjectionInline(admin.TabularInline):
    model = StationYearlyProjection
    extra = 1

@admin.register(StationYearlyProjection)
class StationYearlyProjectionAdmin(admin.ModelAdmin):
    list_display = ('station_financials', 'year', 'projected_utilization', 'projected_sessions', 
                    'projected_revenue', 'projected_profit')
    list_filter = ('year', 'failure_simulated')
    search_fields = ('station_financials__charging_station__name',)

@admin.register(ExitStrategy)
class ExitStrategyAdmin(admin.ModelAdmin):
    list_display = ('project', 'strategy_type', 'name', 'estimated_recovery_percentage', 'implementation_cost')
    list_filter = ('strategy_type',)
    search_fields = ('name', 'project__name', 'description')