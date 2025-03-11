# cpo_planner/projects/views/dashboard.py
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from ..models.project import Project
from ..models.charging_station import ChargingStation

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'projects/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Statistiche progetti
        projects = Project.objects.all()
        context['total_projects'] = projects.count()
        context['active_projects'] = projects.filter(status='in_progress').count()
        context['planning_projects'] = projects.filter(status='planning').count()
        context['completed_projects'] = projects.filter(status='completed').count()
        
        # Statistiche stazioni
        stations = ChargingStation.objects.all()
        context['total_stations'] = stations.count()
        context['active_stations'] = stations.filter(status='active').count()
        context['planned_stations'] = stations.filter(status='planned').count()
        
        # Statistiche finanziarie
        context['total_investment'] = projects.aggregate(Sum('total_budget'))['total_budget__sum'] or 0
        
        # Ultimi progetti
        context['recent_projects'] = projects.order_by('-id')[:5]
        
        # Stazioni recentemente aggiornate
        context['recent_stations'] = stations.order_by('-updated_at')[:5]
        
        # Progetti per regione
        context['projects_by_region'] = projects.values('region').annotate(count=Count('id')).order_by('-count')
        
        # Stazioni per status
        context['stations_by_status'] = stations.values('status').annotate(count=Count('id')).order_by('-count')
        
        return context