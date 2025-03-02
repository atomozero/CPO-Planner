# CPO Planner 
 
Sistema di pianificazione, progettazione e gestione per operatori di punti di ricarica (CPO) per veicoli elettrici. 
 
## Funzionalità 
 
- Analisi finanziaria e previsioni 
- Business plan per progetti di installazione 
- Organizzazione strutturata dei progetti 
- Reportistica dettagliata 
- Integrazione con impianti fotovoltaici 
 
## Installazione 
 
1. Clona il repository 
2. Crea un ambiente virtuale: `python -m venv venv` 
3. Attiva l'ambiente virtuale: 
   - Windows: `venv\Scripts\activate` 
   - Linux/Mac: `source venv/bin/activate` 
4. Installa le dipendenze: `pip install -r requirements.txt` 
5. Esegui le migrazioni: `python manage.py migrate` 
6. Crea un superuser: `python manage.py createsuperuser` 
7. Avvia il server: `python manage.py runserver` 
