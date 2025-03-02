from django.urls import path
from . import views

urlpatterns = [
    # Dashboard finanziaria
    path('', views.financial_dashboard, name='financial_dashboard'),
    
    # Placeholder URLs (da implementare)
    path('reports/', lambda request: None, name='report_list'),
]
