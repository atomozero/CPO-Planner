# admin.py
from django.contrib import admin
from .models import Municipality, ChargingProject, ChargingStation, ProjectTask

@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'province', 'population', 'ev_adoption_rate')
    search_fields = ('name', 'province')

@admin.register(ChargingProject)
class ChargingProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'status', 'budget')
    list_filter = ('status', 'municipality')
    search_fields = ('name',)

@admin.register(ChargingStation)
class ChargingStationAdmin(admin.ModelAdmin):
    list_display = ('code', 'project', 'location', 'status', 'connection_type')
    list_filter = ('status', 'connection_type', 'project')
    search_fields = ('code', 'location')

@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'status', 'priority', 'planned_start_date', 'planned_end_date')
    list_filter = ('status', 'priority', 'project')
    search_fields = ('name',)