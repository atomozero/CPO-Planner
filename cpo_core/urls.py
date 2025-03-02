from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Organization URLs
    path('organizations/', views.OrganizationListView.as_view(), name='organization_list'),
    path('organizations/<int:pk>/', views.OrganizationDetailView.as_view(), name='organization_detail'),
    path('organizations/create/', views.OrganizationCreateView.as_view(), name='organization_create'),
    path('organizations/<int:pk>/update/', views.OrganizationUpdateView.as_view(), name='organization_update'),
    path('organizations/<int:pk>/delete/', views.OrganizationDeleteView.as_view(), name='organization_delete'),
    
    # Project URLs
    path('projects/', views.ProjectListView.as_view(), name='project_list'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('projects/create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('projects/<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    path('projects/<int:pk>/delete/', views.ProjectDeleteView.as_view(), name='project_delete'),
    
    # Municipality URLs
    path('municipalities/', views.MunicipalityListView.as_view(), name='municipality_list'),
    
    # ChargingStation URLs
    path('stations/', views.ChargingStationListView.as_view(), name='station_list'),
    
    # Placeholder URLs per navigazione (da implementare)
    path('profile/', lambda request: None, name='profile'),
    path('settings/', lambda request: None, name='settings'),
]
