#!/usr/bin/env python
# debug_municipality.py
# Esegui con: python debug_municipality.py

import os
import django

# Configura Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cpo_planner.settings')
django.setup()

# Importa i modelli
from cpo_core.models.project import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.municipality import Municipality

# Funzione di test per aggiornare il comune di un progetto
def test_update_municipality(project_id, municipality_id):
    try:
        project = Project.objects.get(id=project_id)
        municipality = Municipality.objects.get(id=municipality_id)
        
        print(f"\nSTATO INIZIALE:")
        print(f"Progetto: {project.id} - {project.name}")
        print(f"Comune attuale: {project.municipality_id} - {getattr(project.municipality, 'name', 'Nessuno')}")
        print(f"Nuovo comune: {municipality.id} - {municipality.name}")
        
        # Verifica sottoprogetti prima dell'aggiornamento
        subprojects = SubProject.objects.filter(project=project)
        print(f"\nSOTTOPROGETTI PRIMA dell'aggiornamento:")
        for sp in subprojects:
            print(f"  - {sp.id}: {sp.name}, Comune: {sp.municipality_id} - {getattr(sp.municipality, 'name', 'Nessuno')}")
        
        # Aggiorna il comune del progetto
        project.municipality = municipality
        project.save()
        
        # Ricarica il progetto dal database
        project.refresh_from_db()
        
        print(f"\nSTATO DOPO AGGIORNAMENTO:")
        print(f"Progetto: {project.id} - {project.name}")
        print(f"Comune aggiornato: {project.municipality_id} - {getattr(project.municipality, 'name', 'Nessuno')}")
        
        # Verifica sottoprogetti dopo l'aggiornamento
        subprojects = SubProject.objects.filter(project=project)
        print(f"\nSOTTOPROGETTI DOPO l'aggiornamento:")
        for sp in subprojects:
            sp.refresh_from_db()  # Assicurati di avere dati aggiornati
            print(f"  - {sp.id}: {sp.name}, Comune: {sp.municipality_id} - {getattr(sp.municipality, 'name', 'Nessuno')}")
        
        return True
    except Exception as e:
        print(f"ERRORE: {e}")
        return False

# Estrai il primo comune disponibile
try:
    first_municipality = Municipality.objects.first()
    if first_municipality:
        print(f"Trovato comune: {first_municipality.id} - {first_municipality.name}")
        
        # Test con il primo progetto disponibile
        first_project = Project.objects.first()
        if first_project:
            print(f"Trovato progetto: {first_project.id} - {first_project.name}")
            
            # Esegui il test
            test_update_municipality(first_project.id, first_municipality.id)
        else:
            print("Nessun progetto trovato nel database")
    else:
        print("Nessun comune trovato nel database")
except Exception as e:
    print(f"Errore generale: {e}")
