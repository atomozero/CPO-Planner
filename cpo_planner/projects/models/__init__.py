# cpo_planner/projects/models/__init__.py


# Prima importa i modelli base che non dipendono da altri
from .project import Project
from .municipality import Municipality
from .subproject import SubProject  # Nota il nome file corretto 'subproject.py', non 'sub_project.py'

# Poi importa i modelli che dipendono dai precedenti
from .charging_station import ChargingStation

# Esporta tutti i modelli
__all__ = [
    'Project',
    'Municipality',
    'SubProject',
    'ChargingStation',
]