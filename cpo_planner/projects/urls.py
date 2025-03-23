# cpo_planner/projects/urls.py
from django.urls import path
from .views.dashboard import DashboardView
from .views.project_views import (
    ProjectListView, ProjectDetailView, ProjectCreateView, ProjectUpdateView, ProjectDeleteView
)
from .views.subproject_views import (
    SubProjectDetailView, SubProjectCreateView, SubProjectUpdateView, SubProjectDeleteView
)
from .views.charging_station_views import (
    ChargingStationDetailView, ChargingStationCreateView, ChargingStationUpdateView, ChargingStationDeleteView,
    ChargerListView, ChargerDetailView, ChargerCreateView, ChargerUpdateView, ChargerDeleteView,
    ChargingStationPhotoCreateView, ChargingStationPhotoUpdateView, ChargingStationPhotoDetailView, ChargingStationPhotoDeleteView,
    usage_profile_detail  # Nuova importazione per l'endpoint API
)
from .views.financial_views import (
    FinancialParametersUpdateView, RunFinancialAnalysisView,
    ProjectFinancialResultsView, StationFinancialResultsView
)
from .views.photovoltaic_views import (
    PhotovoltaicDetailView, PhotovoltaicCreateView, PhotovoltaicUpdateView, PhotovoltaicDeleteView
)
from .views.timeline_views import (
    ProjectTimelineDetailView, ProjectTimelineCreateUpdateView,
    StationTimelineDetailView, StationTimelineCreateUpdateView
)
from .views.report_views import (
    ProjectReportView, StationReportView, MunicipalityReportView
)
from .views.failure_simulation_views import (
    FailureSimulationView, RunFailureSimulationView, FailureSimulationResultsView
)

app_name = 'projects'

urlpatterns = [
    # Dashboard
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    
    # Project views
    path('', ProjectListView.as_view(), name='project_list'),
    path('create/', ProjectCreateView.as_view(), name='project_create'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('<int:pk>/update/', ProjectUpdateView.as_view(), name='project_update'),
    path('<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),
    
    # SubProject views
    path('<int:project_id>/subproject/create/', SubProjectCreateView.as_view(), name='subproject_create'),
    path('subproject/<int:pk>/', SubProjectDetailView.as_view(), name='subproject_detail'),
    path('subproject/<int:pk>/update/', SubProjectUpdateView.as_view(), name='subproject_update'),
    path('subproject/<int:pk>/delete/', SubProjectDeleteView.as_view(), name='subproject_delete'),
    path('subproject/<int:pk>/update-status/<str:status>/', SubProjectUpdateView.as_view(
        template_name='projects/subproject_status_form.html',
        fields=['status']
    ), name='subproject_update_status'),
    
    # ChargingStation views
    path('subproject/<int:subproject_id>/station/create/', ChargingStationCreateView.as_view(), name='station_create'),
    path('station/<int:pk>/', ChargingStationDetailView.as_view(), name='station_detail'),
    path('station/<int:pk>/update/', ChargingStationUpdateView.as_view(), name='station_update'),
    path('station/<int:pk>/delete/', ChargingStationDeleteView.as_view(), name='station_delete'),
    
    # API endpoint per i profili di utilizzo
    path('api/usage-profiles/<int:profile_id>/', usage_profile_detail, name='api_usage_profile_detail'),
    
    # Financial views
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
    
    # Photovoltaic views
    path('station/<int:station_id>/photovoltaic/create/', 
        PhotovoltaicCreateView.as_view(), 
        name='photovoltaic_create'),
    
    path('photovoltaic/<int:pk>/', 
        PhotovoltaicDetailView.as_view(), 
        name='photovoltaic_detail'),
    
    path('photovoltaic/<int:pk>/update/', 
        PhotovoltaicUpdateView.as_view(), 
        name='photovoltaic_update'),
    
    path('photovoltaic/<int:pk>/delete/', 
        PhotovoltaicDeleteView.as_view(), 
        name='photovoltaic_delete'),
    
    # Timeline views
    path('<int:project_id>/timeline/', 
        ProjectTimelineDetailView.as_view(), 
        name='project_timeline_detail'),
    
    path('<int:project_id>/timeline/edit/', 
        ProjectTimelineCreateUpdateView.as_view(), 
        name='project_timeline_edit'),
    
    path('<int:project_id>/station/<int:station_id>/timeline/', 
        StationTimelineDetailView.as_view(), 
        name='station_timeline_detail'),
    
    path('<int:project_id>/station/<int:station_id>/timeline/edit/', 
        StationTimelineCreateUpdateView.as_view(), 
        name='station_timeline_edit'),
    
    # Report views
    path('<int:project_id>/report/', 
        ProjectReportView.as_view(), 
        name='project_report'),
    
    path('<int:project_id>/station/<int:station_id>/report/', 
        StationReportView.as_view(), 
        name='station_report'),
    
    path('<int:project_id>/subproject/<int:subproject_id>/municipality-report/', 
        MunicipalityReportView.as_view(), 
        name='municipality_report'),
    
    # Failure Simulation views
    path('<int:project_id>/failure-simulation/', 
        FailureSimulationView.as_view(), 
        name='failure_simulation_form'),
    
    path('<int:project_id>/run-failure-simulation/', 
        RunFailureSimulationView.as_view(), 
        name='run_failure_simulation'),
    
    path('<int:project_id>/failure-simulation-results/', 
        FailureSimulationResultsView.as_view(), 
        name='failure_simulation_results'),
        
    # Charger views (new)
    path('subproject/<int:subproject_id>/chargers/', 
        ChargerListView.as_view(), 
        name='charger_list'),
        
    path('subproject/<int:subproject_id>/chargers/add/', 
        ChargerCreateView.as_view(), 
        name='charger_create'),
        
    # Charger views for charging stations
    path('station/<uuid:charging_station_id>/chargers/', 
        ChargerListView.as_view(), 
        name='station_charger_list'),
        
    path('station/<uuid:charging_station_id>/chargers/add/', 
        ChargerCreateView.as_view(), 
        name='station_charger_create'),
        
    path('charger/<int:pk>/', 
        ChargerDetailView.as_view(), 
        name='charger_detail'),
        
    path('charger/<int:pk>/update/', 
        ChargerUpdateView.as_view(), 
        name='charger_update'),
        
    path('charger/<int:pk>/delete/', 
        ChargerDeleteView.as_view(), 
        name='charger_delete'),
        
    # Charging Station Photo views
    path('station/<station_id>/photo/add/', 
        ChargingStationPhotoCreateView.as_view(), 
        name='charging_station_add_photo'),
        
    path('station/photo/<pk>/', 
        ChargingStationPhotoDetailView.as_view(), 
        name='charging_station_photo_detail'),
        
    path('station/photo/<pk>/edit/', 
        ChargingStationPhotoUpdateView.as_view(), 
        name='charging_station_photo_edit'),
        
    path('station/photo/<pk>/delete/', 
        ChargingStationPhotoDeleteView.as_view(), 
        name='charging_station_photo_delete'),
]