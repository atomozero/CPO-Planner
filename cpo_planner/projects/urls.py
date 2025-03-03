from django.urls import path
from .views.base import (
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView,
    MunicipalityCreateView, MunicipalityUpdateView, MunicipalityDeleteView,
    ChargingStationCreateView, ChargingStationDetailView, ChargingStationUpdateView, ChargingStationDeleteView
)
from .views.financial import (
    FinancialParametersUpdateView, RunFinancialAnalysisView,
    ProjectFinancialResultsView, StationFinancialResultsView
)

app_name = 'projects'

urlpatterns = [
    # Viste per Project
    path('', ProjectListView.as_view(), name='project_list'),
    path('create/', ProjectCreateView.as_view(), name='project_create'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('<int:pk>/update/', ProjectUpdateView.as_view(), name='project_update'),
    path('<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),
    
    # Viste per Municipality
    path('<int:project_id>/municipality/create/', MunicipalityCreateView.as_view(), name='municipality_create'),
    path('municipality/<int:pk>/update/', MunicipalityUpdateView.as_view(), name='municipality_update'),
    path('municipality/<int:pk>/delete/', MunicipalityDeleteView.as_view(), name='municipality_delete'),
    
    # Viste per ChargingStation
    path('municipality/<int:municipality_id>/station/create/', ChargingStationCreateView.as_view(), name='station_create'),
    path('<int:project_id>/station/<int:pk>/', ChargingStationDetailView.as_view(), name='station_detail'),
    path('station/<int:pk>/update/', ChargingStationUpdateView.as_view(), name='station_update'),
    path('station/<int:pk>/delete/', ChargingStationDeleteView.as_view(), name='station_delete'),
    
    # Viste per Financial Analysis
    path('<int:project_id>/financial-parameters/', 
         FinancialParametersUpdateView.as_view(), 
         name='financial_parameters'),
    
    path('<int:project_id>/run-financial-analysis/', 
         RunFinancialAnalysisView.as_view(), 
         name='run_project_analysis'),
    
    path('<int:project_id>/station/<int:station_id>/run-financial-analysis/', 
         RunFinancialAnalysisView.as_view(), 
         name='run_station_analysis'),
    
    path('<int:project_id>/financial-results/', 
         ProjectFinancialResultsView.as_view(), 
         name='project_financial_results'),
    
    path('<int:project_id>/station/<int:station_id>/financial-results/', 
         StationFinancialResultsView.as_view(), 
         name='station_financial_results'),
]