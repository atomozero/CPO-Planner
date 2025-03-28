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

## Gestione dei Comuni nel Sistema

### Problema Risolto
Il sistema presentava un bug per cui, quando si salvava una Stazione di ricarica, questa cambiava sempre il comune del progetto in "Dolo" (ID 1). Questo comportamento non era corretto.

### Soluzione Implementata
È stata completamente rivista la gestione dei comuni nei progetti e nelle stazioni di ricarica:

1. **Ereditarietà dal Progetto Principale**:
   - Il comune assegnato al progetto principale è ora considerato prevalente.
   - Tutti i sottoprogetti (stazioni di ricarica) ereditano automaticamente il comune dal progetto principale.
   - Quando il comune di un progetto viene modificato, tutti i sottoprogetti vengono automaticamente aggiornati.

2. **Validazione durante il Salvataggio**:
   - Nel metodo `save()` del modello `SubProject` è stato aggiunto un controllo che verifica l'allineamento del comune con quello del progetto principale.
   - Se un sottoprogetto ha un comune diverso dal suo progetto principale, viene automaticamente aggiornato.

3. **Interfaccia Utente**:
   - Nei form di creazione di nuovi sottoprogetti, il campo comune è nascosto poiché viene ereditato dal progetto.
   - Nei form di modifica dei sottoprogetti esistenti, il campo comune è visibile ma disabilitato, con una spiegazione che indica che viene ereditato dal progetto principale.

4. **Gerarchia Chiara**:
   - Il modello `ChargingStation` non gestisce direttamente il comune, ma lo eredita sempre dal sottoprogetto associato.
   - È stata aggiunta una nota nel codice per chiarire questa relazione.

5. **Sincronizzazione Migliorata**:
   - Il metodo `sync_municipalities()` del modello `Project` è stato migliorato per garantire che tutti i sottoprogetti abbiano il comune corretto.
   - È stato aggiunto un sistema di recupero per i casi in cui l'aggiornamento standard fallisca.

### Vantaggi della Nuova Implementazione
- **Consistenza dei Dati**: Tutti i sottoprogetti avranno sempre lo stesso comune del progetto principale.
- **Manutenibilità**: Modificare il comune di un progetto aggiorna automaticamente tutti i suoi sottoprogetti.
- **Semplicità d'Uso**: L'utente deve specificare il comune solo a livello di progetto, semplificando l'interfaccia e riducendo gli errori.
- **Debug Migliorato**: Sono stati aggiunti messaggi di debug dettagliati che facilitano l'identificazione di problemi.
