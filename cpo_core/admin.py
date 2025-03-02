from django.contrib import admin
from .models import Organization, Project, Municipality, SubProject, ChargingStation, SolarInstallation

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'tax_id', 'contact_email', 'contact_phone')
    search_fields = ('name', 'tax_id')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'status', 'start_date', 'end_date', 'budget')
    list_filter = ('status', 'organization')
    search_fields = ('name', 'description')

@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'region', 'population')
    list_filter = ('province', 'region')
    search_fields = ('name', 'province', 'region')

@admin.register(SubProject)
class SubProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'municipality', 'status', 'start_date', 'planned_completion_date')
    list_filter = ('status', 'project', 'municipality')
    search_fields = ('name', 'description')

@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ('name', 'subproject', 'station_type', 'status', 'power_kw', 'total_cost')
    list_filter = ('status', 'station_type', 'subproject__municipality')
    search_fields = ('name', 'address')
    readonly_fields = ('total_cost',)

@admin.register(SolarInstallation)
class SolarInstallationAdmin(admin.ModelAdmin):
    list_display = ('charging_station', 'capacity_kw', 'num_panels', 'annual_production_kwh')
    search_fields = ('charging_station__name',)