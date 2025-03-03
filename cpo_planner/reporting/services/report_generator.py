# cpo_planner/reporting/services/report_generator.py
import os
from django.utils import timezone
from django.conf import settings

def generate_report_async(report_id):
    """
    Genera un report in modo non-bloccante (ma sincronizzata per compatibilità con Celery)
    
    Args:
        report_id: ID del report da generare
    
    Returns:
        tuple: (success, message)
    """
    # Importazione qui per evitare importazioni circolari
    from ..models import Report
    
    try:
        # Recupera il report
        report = Report.objects.get(id=report_id)
        
        # Aggiorna lo stato
        report.status = 'generating'
        report.generation_error = ''
        report.save(update_fields=['status', 'generation_error'])
        
        # Genera contenuto del report (da implementare con una vera logica)
        # In un'implementazione reale, qui genereresti un PDF o altro formato
        # usando le informazioni del report e i valori dei placeholder
        
        # Esempio: salva un file PDF vuoto per test
        report_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
        os.makedirs(report_dir, exist_ok=True)
        
        report_filename = f"report_{report_id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
        report_path = os.path.join(report_dir, report_filename)
        
        # Crea un file vuoto per test
        with open(report_path, 'wb') as f:
            f.write(b'%PDF-1.5\n%Test PDF\n')
        
        # Aggiorna il report
        report.generated_file = f'reports/{report_filename}'
        report.generated_at = timezone.now()
        report.status = 'completed'
        report.save(update_fields=['generated_file', 'generated_at', 'status'])
        
        return True, "Report generato con successo"
        
    except Report.DoesNotExist:
        return False, "Report non trovato"
    except Exception as e:
        # In caso di errore, aggiorna lo stato del report
        try:
            report.status = 'failed'
            report.generation_error = str(e)
            report.save(update_fields=['status', 'generation_error'])
        except:
            pass
        
        return False, str(e)