# environmental/urls.py
from django.urls import path
from . import views

app_name = 'environmental'

urlpatterns = [
    # Dashboard
    path('', 
         views.EnvironmentalDashboardView.as_view(), 
         name='dashboard'),
    
    # Fattori di emissione
    path('fattori-emissione/', 
         views.EmissionFactorListView.as_view(), 
         name='emission_factor_list'),
    path('fattori-emissione/<int:pk>/', 
         views.EmissionFactorDetailView.as_view(), 
         name='emission_factor_detail'),
    path('fattori-emissione/nuovo/', 
         views.EmissionFactorCreateView.as_view(), 
         name='emission_factor_create'),
    path('fattori-emissione/<int:pk>/modifica/', 
         views.EmissionFactorUpdateView.as_view(), 
         name='emission_factor_update'),
    path('fattori-emissione/<int:pk>/elimina/', 
         views.EmissionFactorDeleteView.as_view(), 
         name='emission_factor_delete'),
    
    # Tipi di veicolo
    path('tipi-veicolo/', 
         views.VehicleTypeListView.as_view(), 
         name='vehicle_type_list'),
    path('tipi-veicolo/<int:pk>/', 
         views.VehicleTypeDetailView.as_view(), 
         name='vehicle_type_detail'),
    path('tipi-veicolo/nuovo/', 
         views.VehicleTypeCreateView.as_view(), 
         name='vehicle_type_create'),
    path('tipi-veicolo/<int:pk>/modifica/', 
         views.VehicleTypeUpdateView.as_view(), 
         name='vehicle_type_update'),
    path('tipi-veicolo/<int:pk>/elimina/', 
         views.VehicleTypeDeleteView.as_view(), 
         name='vehicle_type_delete'),
    
    # Analisi ambientali
    path('analisi/', 
         views.EnvironmentalAnalysisListView.as_view(), 
         name='analysis_list'),
    path('analisi/<int:pk>/', 
         views.EnvironmentalAnalysisDetailView.as_view(), 
         name='analysis_detail'),
    path('analisi/nuova/', 
         views.EnvironmentalAnalysisCreateView.as_view(), 
         name='analysis_create'),
    path('analisi/nuova/<str:entity_type>/<int:entity_id>/', 
         views.EnvironmentalAnalysisCreateView.as_view(), 
         name='analysis_create_entity'),
    path('analisi/<int:pk>/modifica/', 
         views.EnvironmentalAnalysisUpdateView.as_view(), 
         name='analysis_update'),
    path('analisi/<int:pk>/elimina/', 
         views.EnvironmentalAnalysisDeleteView.as_view(), 
         name='analysis_delete'),
    path('analisi/<int:pk>/ricalcola/', 
         views.RecalculateAnalysisView.as_view(), 
         name='analysis_recalculate'),
    
    # API
    path('api/analisi/<int:pk>/dati/', 
         views.analysis_data_api, 
         name='analysis_data_api'),
]
