from django.urls import path
from . import views

app_name = 'financial'

urlpatterns = [
    # Dashboard finanziaria
    path('', views.financial_dashboard, name='dashboard'),
    
    # Placeholder URLs (da implementare)
    path('reports/', lambda request: None, name='report_list'),
]
