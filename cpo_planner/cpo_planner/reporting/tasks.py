# reporting/tasks.py
from celery import shared_task
import logging
from .services import generate_report_async

logger = logging.getLogger(__name__)

@shared_task
def generate_report_task(report_id):
    """Task Celery per generare report in background"""
    logger.info(f"Avvio generazione report {report_id}")
    
    try:
        success, message = generate_report_async(report_id)
        
        if success:
            logger.info(f"Report {report_id} generato con successo: {message}")
            return True
        else:
            logger.error(f"Errore nella generazione del report {report_id}: {message}")
            return False
    except Exception as e:
        logger.exception(f"Eccezione durante la generazione del report {report_id}: {str(e)}")
        return False
