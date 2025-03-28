# cpo_core/signals.py
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.db import transaction
from cpo_core.models.project import Project

@receiver(post_save, sender=Project)
def update_subprojects_municipality(sender, instance, created, **kwargs):
    """
    Quando un progetto viene salvato, sincronizza il comune con i sottoprogetti
    se il campo 'municipality' è stato impostato.
    """
    # Usa una transazione per garantire consistenza
    with transaction.atomic():
        # Verifica se il comune è impostato
        if instance.municipality:
            # Stampa info di debug
            print(f"SIGNAL post_save: Progetto {instance.id} salvato, municipality: {instance.municipality.id}")
            
            # Ricarica l'istanza dal database per essere sicuri di avere i dati aggiornati
            instance.refresh_from_db()
            print(f"SIGNAL post_save: Dopo refresh_from_db, municipality: {instance.municipality.id}")
            
            # Sincronizza i sottoprogetti
            updated = instance.sync_municipalities()
            print(f"SIGNAL post_save: Sincronizzazione completata, aggiornati: {updated}")
            
            # Verifica che i sottoprogetti siano effettivamente aggiornati
            from cpo_core.models.subproject import SubProject
            subprojects = SubProject.objects.filter(project=instance).values('id', 'name', 'municipality_id')
            print(f"SIGNAL post_save: Stato sottoprogetti dopo aggiornamento: {list(subprojects)}")
            
            # Verifica che tutti abbiano lo stesso ID municipio del progetto
            incorrect = [s for s in subprojects if s['municipality_id'] != instance.municipality.id]
            if incorrect:
                print(f"WARNING: I seguenti sottoprogetti non hanno il municipio corretto: {incorrect}")
                # Correzione forzata per i sottoprogetti non aggiornati correttamente
                SubProject.objects.filter(id__in=[s['id'] for s in incorrect]).update(municipality=instance.municipality)