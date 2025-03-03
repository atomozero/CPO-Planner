# reporting/urls.py
from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Template di report
    path('templates/', 
         views.ReportTemplateListView.as_view(), 
         name='template_list'),
    path('templates/<int:pk>/', 
         views.ReportTemplateDetailView.as_view(), 
         name='template_detail'),
    path('templates/nuovo/', 
         views.ReportTemplateCreateView.as_view(), 
         name='template_create'),
    path('templates/<int:pk>/modifica/', 
         views.ReportTemplateUpdateView.as_view(), 
         name='template_update'),
    path('templates/<int:pk>/elimina/', 
         views.ReportTemplateDeleteView.as_view(), 
         name='template_delete'),
    
    # Gestione report
    path('', 
         views.ReportListView.as_view(), 
         name='report_list'),
    path('<int:pk>/', 
         views.ReportDetailView.as_view(), 
         name='report_detail'),
    path('nuovo/', 
         views.ReportCreateView.as_view(), 
         name='report_create'),
    path('nuovo/<str:entity_type>/<int:entity_id>/', 
         views.ReportCreateView.as_view(), 
         name='report_create_entity'),
    path('<int:pk>/elimina/', 
         views.ReportDeleteView.as_view(), 
         name='report_delete'),
    path('<int:pk>/rigenera/', 
         views.RegenerateReportView.as_view(), 
         name='report_regenerate'),
    path('<int:pk>/download/', 
         views.DownloadReportView.as_view(), 
         name='report_download'),
    path('<int:pk>/anteprima/', 
         views.ReportPreviewView.as_view(), 
         name='report_preview'),
    path('<int:pk>/status/', 
         views.report_status_api, 
         name='report_status_api'),
         
    # Creazione in blocco
    path('crea-in-blocco/', 
         views.ReportBulkCreateView.as_view(), 
         name='report_bulk_create'),
]