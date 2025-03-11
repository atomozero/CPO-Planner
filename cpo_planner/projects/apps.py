# cpo_planner/projects/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cpo_planner.projects'
    verbose_name = _('Progetti')