# documents/urls.py
from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # Lista documenti
    path('', views.DocumentListView.as_view(), name='document_list'),
    path('<str:entity_type>/<int:entity_id>/', 
         views.DocumentListView.as_view(), 
         name='document_list_entity'),
    
    # Gestione documenti
    path('documento/<int:pk>/', 
         views.DocumentDetailView.as_view(), 
         name='document_detail'),
    path('nuovo/', 
         views.DocumentCreateView.as_view(), 
         name='document_create'),
    path('nuovo/<str:entity_type>/<int:entity_id>/', 
         views.DocumentCreateView.as_view(), 
         name='document_create_entity'),
    path('modifica/<int:pk>/', 
         views.DocumentUpdateView.as_view(), 
         name='document_update'),
    path('elimina/<int:pk>/', 
         views.DocumentDeleteView.as_view(), 
         name='document_delete'),
    path('download/<int:pk>/', 
         views.DocumentDownloadView.as_view(), 
         name='document_download'),
    path('anteprima/<int:pk>/', 
         views.DocumentPreviewView.as_view(), 
         name='document_preview'),
    path('stato/<int:pk>/', 
         views.update_document_status, 
         name='update_document_status'),
         
    # Note e attività
    path('documento/<int:pk>/aggiungi-nota/', 
         views.AddDocumentNoteView.as_view(), 
         name='add_document_note'),
    path('documento/<int:pk>/aggiungi-attivita/', 
         views.AddDocumentTaskView.as_view(), 
         name='add_document_task'),
    path('attivita/<int:pk>/aggiorna-stato/', 
         views.UpdateDocumentTaskView.as_view(), 
         name='update_task_status'),
         
    # Categorie documenti
    path('categorie/', 
         views.DocumentCategoryListView.as_view(), 
         name='category_list'),
    path('categorie/nuova/', 
         views.DocumentCategoryCreateView.as_view(), 
         name='category_create'),
    path('categorie/modifica/<int:pk>/', 
         views.DocumentCategoryUpdateView.as_view(), 
         name='category_update'),
    path('categorie/elimina/<int:pk>/', 
         views.DocumentCategoryDeleteView.as_view(), 
         name='category_delete'),
]
