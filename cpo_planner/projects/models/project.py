# cpo_planner/projects/models/project.py

# Importa il modello originale da cpo_core
from cpo_core.models.project import Project as CoreProject
from cpo_core.models.project import project_logo_path

# Crea un modello proxy nell'app projects
class Project(CoreProject):
    """
    Proxy model per il Project della cpo_core.
    Necessario per mantenere le relazioni tra i modelli nelle diverse app.
    """
    class Meta:
        proxy = True
        app_label = 'projects'

# Re-esporta tutto ciò che potrebbe essere necessario
__all__ = ['Project', 'project_logo_path']