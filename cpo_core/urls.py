#cpo_core/urls.py
from django.urls import path
from . import views
from .views import (
    OrganizationListView, OrganizationDetailView, OrganizationCreateView, 
    OrganizationUpdateView, OrganizationDeleteView,
    ProjectListView, ProjectDetailView, ProjectCreateView, 
    ProjectUpdateView, ProjectDeleteView,
    MunicipalityListView, ChargingStationListView, MunicipalityCreateView
)

app_name = 'cpo_core'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Organizzazioni
    path('organizations/', OrganizationListView.as_view(), name='organization_list'),
    path('organizations/<int:pk>/', OrganizationDetailView.as_view(), name='organization_detail'),
    path('organizations/new/', OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/<int:pk>/edit/', OrganizationUpdateView.as_view(), name='organization_update'),
    path('organizations/<int:pk>/delete/', OrganizationDeleteView.as_view(), name='organization_delete'),
    
    # Progetti (rimossi per evitare conflitti con cpo_planner.projects)
    # Questi URL sono ora gestiti da cpo_planner.projects.urls
    
    # Proiezioni finanziarie
    path('financial-overview/', views.financial_overview, name='financial_overview'),
    path('financial-project/<int:pk>/', views.project_financial_detail, name='project_financial_detail'),
    path('financial-project/<int:project_id>/create/', views.financial_projection_create, name='financial_projection_create'),
    path('financial-projection/<int:pk>/update/', views.financial_projection_update, name='financial_projection_update'),
    path('financial-roi-calculator/', views.roi_calculator, name='roi_calculator'),
    
    # Comuni
    path('municipalities/', MunicipalityListView.as_view(), name='municipality_list'),
    path('municipalities/add/', MunicipalityCreateView.as_view(), name='municipality_create'),

    # Stazioni di ricarica
    path('stations/', ChargingStationListView.as_view(), name='station_list'),
]