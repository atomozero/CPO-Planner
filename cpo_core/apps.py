# cpo_core/apps.py
from django.apps import AppConfig

class CpoCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'cpo_core'
    verbose_name = 'CPO Core'