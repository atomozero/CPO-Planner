# mapping/urls.py
from django.urls import path
from . import views

app_name = 'mapping'

urlpatterns = [
    # Vista principale della mappa
    path('', 
         views.MapView.as_view(), 
         name='map_view'),
    path('progetto/<int:project_id>/', 
         views.MapView.as_view(), 
         name='map_view_project'),
    path('sotto-progetto/<int:subproject_id>/', 
         views.MapView.as_view(), 
         name='map_view_subproject'),
    path('mappa/<int:map_id>/', 
         views.MapView.as_view(), 
         name='map_view_saved'),
    
    # Impostazioni mappa
    path('impostazioni/', 
         views.MapSettingsListView.as_view(), 
         name='settings_list'),
    path('impostazioni/nuove/', 
         views.MapSettingsCreateView.as_view(), 
         name='settings_create'),
    path('impostazioni/<int:pk>/modifica/', 
         views.MapSettingsUpdateView.as_view(), 
         name='settings_update'),
    path('impostazioni/<int:pk>/elimina/', 
         views.MapSettingsDeleteView.as_view(), 
         name='settings_delete'),
    
    # Marker personalizzati
    path('marker/', 
         views.CustomMarkerListView.as_view(), 
         name='marker_list'),
    path('marker/nuovo/', 
         views.CustomMarkerCreateView.as_view(), 
         name='marker_create'),
    path('marker/<int:pk>/modifica/', 
         views.CustomMarkerUpdateView.as_view(), 
         name='marker_update'),
    path('marker/<int:pk>/elimina/', 
         views.CustomMarkerDeleteView.as_view(), 
         name='marker_delete'),
    
    # Mappe salvate
    path('mappe-salvate/', 
         views.SavedMapListView.as_view(), 
         name='saved_map_list'),
    path('mappe-salvate/nuova/', 
         views.SavedMapCreateView.as_view(), 
         name='saved_map_create'),
    path('mappe-salvate/<int:pk>/modifica/', 
         views.SavedMapUpdateView.as_view(), 
         name='saved_map_update'),
    path('mappe-salvate/<int:pk>/elimina/', 
         views.SavedMapDeleteView.as_view(), 
         name='saved_map_delete'),
    
    # API per dati GeoJSON
    path('api/stazioni/', 
         views.get_stations_geojson, 
         name='api_stations_geojson'),
    path('api/marker/', 
         views.get_custom_markers_geojson, 
         name='api_markers_geojson'),
    path('api/mappa/<int:map_id>/', 
         views.get_saved_map_data, 
         name='api_saved_map_data'),
]