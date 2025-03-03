# cpo_planner/reporting/services/__init__.py
from .report_generator import generate_report_async
from .bulk_operations import generate_bulk_reports

# Esporta le funzioni in modo esplicito
__all__ = ['generate_report_async', 'generate_bulk_reports']