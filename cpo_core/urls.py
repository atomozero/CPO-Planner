#cpo_core/urls.py
from django.urls import path
from . import views
from .views import (
    OrganizationListView, OrganizationDetailView, OrganizationCreateView, 
    OrganizationUpdateView, OrganizationDeleteView,
    ProjectListView, ProjectDetailView, ProjectCreateView, 
    ProjectUpdateView, ProjectDeleteView,
    ChargingStationListView
)

app_name = 'cpo_core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_simple, name='dashboard'),
    
    # Projects (using the same URL structure as the projects app)
    path('projects/', ProjectListView.as_view(), name='project_list'),
    path('projects/create/', ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project_detail'),
    path('projects/<int:pk>/update/', ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),
    
    # Organizzazioni
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('organizations/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('organizations/new/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/<int:pk>/edit/', OrganizationUpdateView.as_view(), name='organization_update'),
    path('organizations/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization_delete'),
    
    # Proiezioni finanziarie
    path('financial-overview/', views.financial_overview, name='financial_overview'),
    path('financial-project/<int:pk>/', views.project_financial_detail, name='project_financial_detail'),
    path('financial-project/<int:project_id>/create/', views.financial_projection_create, name='financial_projection_create'),
    path('financial-projection/<int:pk>/update/', views.financial_projection_update, name='financial_projection_update'),
    path('financial-roi-calculator/', views.roi_calculator, name='roi_calculator'),
    
    # Stazioni di ricarica
    path('stations/', ChargingStationListView.as_view(), name='station_list'),
    path('stations/<uuid:pk>/', views.ChargingStationDetailView.as_view(), name='charging_station_detail'),
    path('stations/<uuid:pk>/calculations/', views.charging_station_calculations, name='charging_station_calculations'),
    # Per supportare anche subproject (che hanno ID numerici)
    path('stations/subproject/<int:subproject_id>/calculations/', views.charging_station_calculations_subproject, name='charging_station_calculations_subproject'),
]