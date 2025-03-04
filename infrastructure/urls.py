# urls.py
from django.urls import path
from . import views

app_name = 'infrastructure' 

urlpatterns = [
    # Comuni
    path('municipalities/', views.MunicipalityListView.as_view(), name='municipality-list'),
    path('municipalities/<int:pk>/', views.MunicipalityDetailView.as_view(), name='municipality-detail'),
    path('municipalities/add/', views.MunicipalityCreateView.as_view(), name='municipality-create'),
    path('municipalities/import/', views.ImportMunicipalitiesView.as_view(), name='import_municipalities'),
    path('api/municipalities/autocomplete/', views.municipality_autocomplete, name='municipality-autocomplete'),
    # Progetti
    path('projects/', views.ChargingProjectListView.as_view(), name='project-list'),
    path('projects/<int:pk>/', views.ChargingProjectDetailView.as_view(), name='project-detail'),
    path('projects/add/', views.ChargingProjectCreateView.as_view(), name='project-create'),
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
]