# cpo_planner/projects/models/__init__.py
from .project import Project
from .subproject import SubProject
from .municipality import Municipality
from .charging_station import ChargingStation
from .financial import FinancialParameters, FinancialAnalysis
from .photovoltaic import PhotovoltaicSystem
from .timeline import ProjectTimeline, StationTimeline
from .energy_contract import EnergyContract, ProjectEnergyContract
from .failure_simulation import FailureSimulation
from .document import ProjectDocument, StationDocument

# Assicurarsi che i modelli siano registrati in Django
__all__ = [
    'Project',
    'SubProject',
    'Municipality',
    'ChargingStation',
    'FinancialParameters',
    'FinancialAnalysis',
    'PhotovoltaicSystem',
    'ProjectTimeline',
    'StationTimeline',
    'EnergyContract',
    'ProjectEnergyContract',
    'FailureSimulation',
    'ProjectDocument',
    'StationDocument',
]