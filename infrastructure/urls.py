# urls.py
from django.urls import path
from . import views

app_name = 'infrastructure' 

urlpatterns = [
    # Dashboard principale
    path('', views.dashboard, name='dashboard'),
    
    # Comuni
    path('municipalities/', views.MunicipalityListView.as_view(), name='municipality-list'),
    path('municipalities/<int:pk>/', views.MunicipalityDetailView.as_view(), name='municipality-detail'),
    path('municipalities/add/', views.MunicipalityCreateView.as_view(), name='municipality-create'),
    path('municipalities/<int:pk>/edit/', views.MunicipalityUpdateView.as_view(), name='municipality-update'),
    path('municipalities/<int:pk>/delete/', views.MunicipalityDeleteView.as_view(), name='municipality-delete'),
    path('municipalities/<int:pk>/upload-logo/', views.municipality_upload_logo, name='municipality-upload-logo'),
    path('municipalities/<int:municipality_id>/test-upload/', views.municipality_test_upload, name='municipality-test-upload'),
    path('municipalities/<int:pk>/update-coordinates/', views.update_municipality_coordinates, name='update-municipality-coordinates'),
    path('municipalities/import/', views.ImportMunicipalitiesView.as_view(), name='import_municipalities'),
    path('municipalities/run-import/', views.RunImportView.as_view(), name='run_import'),
    path('api/municipalities/autocomplete/', views.municipality_autocomplete, name='municipality-autocomplete'),
    # Progetti
    path('projects/', views.ChargingProjectListView.as_view(), name='project-list'),
    path('projects/<int:pk>/', views.ChargingProjectDetailView.as_view(), name='project-detail'),
    path('projects/add/', views.ChargingProjectCreateView.as_view(), name='project-create'),
    path('projects/<int:pk>/edit/', views.ChargingProjectUpdateView.as_view(), name='project-update'),
    path('projects/<int:pk>/delete/', views.ChargingProjectDeleteView.as_view(), name='project-delete'),
    path('municipalities/<int:municipality_id>/projects/add/', views.ChargingProjectCreateView.as_view(), name='municipality-project-create'),
    
    # Stazioni di ricarica
    path('stations/', views.ChargingStationListView.as_view(), name='station-list'),
    path('stations/<int:pk>/', views.ChargingStationDetailView.as_view(), name='station-detail'),
    path('stations/add/', views.ChargingStationCreateView.as_view(), name='station-create'),
    path('projects/<int:project_id>/stations/add/', views.ChargingStationCreateView.as_view(), name='project-station-create'),

    path('projects/<int:project_id>/tasks/', views.ProjectTaskListView.as_view(), name='project-tasks'),
    path('projects/<int:project_id>/tasks/add/', views.ProjectTaskCreateView.as_view(), name='project-task-create'),
    path('tasks/<int:pk>/edit/', views.ProjectTaskUpdateView.as_view(), name='task-update'),
    path('projects/<int:project_id>/gantt/', views.project_gantt_view, name='project-gantt'),

    path('municipalities/<int:pk>/report/', views.generate_municipality_report, name='municipality-report'),
    path('projects/<int:pk>/report/', views.generate_project_report, name='project-report'),
    path('stations/<int:pk>/sheet/', views.generate_station_sheet, name='station-sheet'),
    
    # Technical Data Management Routes
    path('tech-config/', views.tech_config_dashboard, name='tech-config'),
    path('global-settings/', views.GlobalSettingsView.as_view(), name='global-settings'),
    path('global-settings/<int:pk>/', views.GlobalSettingsUpdateView.as_view(), name='global-settings-update'),
    
    # Electricity Tariff Routes
    path('tariffs/', views.ElectricityTariffListView.as_view(), name='tariff-list'),
    path('tariffs/<int:pk>/', views.ElectricityTariffDetailView.as_view(), name='tariff-detail'),
    path('tariffs/add/', views.ElectricityTariffCreateView.as_view(), name='tariff-create'),
    path('tariffs/add-pun/', views.PunTariffCreateView.as_view(), name='pun-tariff-create'),
    path('tariffs/<int:pk>/edit/', views.ElectricityTariffUpdateView.as_view(), name='tariff-update'),
    
    # PUN Data Routes
    path('pun-data/', views.PunDataListView.as_view(), name='pun-data-list'),
    path('pun-data/download/', views.PunDataDownloadView.as_view(), name='pun-data-download'),
    path('energy-projections/', views.EnergyPriceProjectionListView.as_view(), name='energy-projection-list'),
    
    # Management Fee Routes
    path('fees/', views.ManagementFeeListView.as_view(), name='fee-list'),
    path('fees/<int:pk>/', views.ManagementFeeDetailView.as_view(), name='fee-detail'),
    path('fees/add/', views.ManagementFeeCreateView.as_view(), name='fee-create'),
    path('fees/<int:pk>/edit/', views.ManagementFeeUpdateView.as_view(), name='fee-update'),
    
    # Station Usage Profile Routes
    path('profiles/', views.StationUsageProfileListView.as_view(), name='profile-list'),
    path('profiles/<int:pk>/', views.StationUsageProfileDetailView.as_view(), name='profile-detail'),
    path('profiles/add/', views.StationUsageProfileCreateView.as_view(), name='profile-create'),
    path('profiles/<int:pk>/edit/', views.StationUsageProfileUpdateView.as_view(), name='profile-update'),
    
    # Charging Station Template Routes
    path('templates/', views.ChargingStationTemplateListView.as_view(), name='template-list'),
    path('templates/<int:pk>/', views.ChargingStationTemplateDetailView.as_view(), name='template-detail'),
    path('templates/add/', views.ChargingStationTemplateCreateView.as_view(), name='template-create'),
    path('templates/<int:pk>/edit/', views.ChargingStationTemplateUpdateView.as_view(), name='template-update'),
    path('templates/<int:pk>/pdf/', views.ChargingStationTemplatePrintPDFView.as_view(), name='template-print-pdf'),
    # Quick create station from template
    path('templates/<int:template_id>/create-station/', views.station_from_template, name='station-from-template'),
    path('templates/<int:template_id>/create-station/<int:project_id>/', views.station_from_template, name='project-station-from-template'),
]