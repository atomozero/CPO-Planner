# cpo_planner/reporting/services/bulk_operations.py
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from projects.models.project import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.charging_station import ChargingStation


def generate_bulk_reports(template_id, entity_type=None, entity_ids=None, created_by=None):
    """
    Genera più report in batch
    
    Args:
        template_id: ID del template da utilizzare
        entity_type: Tipo di entità (project, subproject, chargingstation)
        entity_ids: Lista di ID delle entità
        created_by: Utente che crea i report
    
    Returns:
        tuple: (count, report_ids)
    """
    # Importazione qui per evitare importazioni circolari
    from ..models import Report, ReportTemplate
    
    report_ids = []
    count = 0
    
    try:
        template = ReportTemplate.objects.get(id=template_id)
        
        with transaction.atomic():
            if entity_type and entity_ids:
                # Crea report per entità specifiche
                content_type = None
                
                if entity_type == 'project':
                    content_type = ContentType.objects.get_for_model(Project)
                    entities = Project.objects.filter(id__in=entity_ids)
                elif entity_type == 'subproject':
                    content_type = ContentType.objects.get_for_model(SubProject)
                    entities = SubProject.objects.filter(id__in=entity_ids)
                elif entity_type == 'chargingstation':
                    content_type = ContentType.objects.get_for_model(ChargingStation)
                    entities = ChargingStation.objects.filter(id__in=entity_ids)
                
                if content_type and entities:
                    for entity in entities:
                        report = Report.objects.create(
                            template=template,
                            title=f"{template.name} - {entity}",
                            description=template.description,
                            content_type=content_type,
                            object_id=entity.id,
                            created_by=created_by,
                            status='pending'
                        )
                        report_ids.append(report.id)
                        count += 1
            else:
                # Crea un report generico non associato a entità
                report = Report.objects.create(
                    template=template,
                    title=template.name,
                    description=template.description,
                    created_by=created_by,
                    status='pending'
                )
                report_ids.append(report.id)
                count += 1
                
    except ReportTemplate.DoesNotExist:
        pass
    except Exception as e:
        pass
    
    return count, report_ids