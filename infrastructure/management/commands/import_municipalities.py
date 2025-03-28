import os
import pandas as pd
from io import StringIO
import numpy as np
import requests
import json
import time  # Corretto l'import di time
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.cache import cache
from infrastructure.models import Municipality

class Command(BaseCommand):
    help = 'Scarica e importa comuni italiani con popolazione nel database'
    
    """
    Comando per l'importazione della lista dei comuni italiani con dati demografici reali.
    
    Fonti dati:
    1. Lista comuni: ISTAT "Elenco-comuni-italiani.csv"
       URL: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
       
    2. Dati demografici: Usare il dataset di matteocontrini che contiene già i dati demografici
       URL: https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json
    """

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', 
            action='store_true', 
            help='Sovrascrive i dati esistenti',
        )
        
        parser.add_argument(
            '--debug', 
            action='store_true', 
            help='Mostra informazioni di debug',
        )

    def update_progress(self, progress, message="", current_count=None, total_count=None):
        """Aggiorna il progresso dell'importazione nella cache"""
        # Crea un dizionario di base con i valori richiesti
        progress_data = {
            'progress': progress,
            'message': message,
            'timestamp': time.time()
        }
        
        # Aggiungi i conteggi se disponibili
        if current_count is not None:
            progress_data['current_count'] = current_count
        if total_count is not None:
            progress_data['total_count'] = total_count
        
        # Salva nella cache
        cache.set('import_progress', progress_data, timeout=3600)  # timeout di 1 ora
        
        # Log alla console
        self.stdout.write(f"Progresso: {progress}% - {message}")

    def handle(self, *args, **options):
        force = options['force']
        debug = options.get('debug', False)
        
        # Controlla se ci sono già dati nel database
        existing_count = Municipality.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(f'Ci sono già {existing_count} comuni nel database. Usa --force per sovrascriverli.')
            )
            return
            
        # Se force è True, cancella i comuni esistenti
        if force and existing_count > 0:
            self.update_progress(2, f"Cancellazione di {existing_count} comuni esistenti...")
            self.stdout.write(self.style.WARNING(f'Cancellazione di {existing_count} comuni esistenti...'))
            Municipality.objects.all().delete()
        
        # Scarica i dati da matteocontrini/comuni-json che include già i dati demografici
        self.update_progress(5, "Scaricamento dati demografici da fonte diretta...")
        self.stdout.write("Scaricamento dati demografici da fonte diretta...")
        url_source = "https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json"
        
        try:
            # Aggiorna il progresso: inizio download
            self.update_progress(10, "Download dati in corso...")
            response = requests.get(url_source)
            response.raise_for_status()
            
            comuni_json = response.json()
            
            # Analizziamo la struttura di un campione
            if debug and len(comuni_json) > 0:
                sample = comuni_json[0]
                self.stdout.write(f"Esempio di struttura dati: {json.dumps(sample, indent=2)}")
            
            # Convertiamo JSON in DataFrame
            self.update_progress(15, "Processamento dati...")
            df = pd.DataFrame(comuni_json)
            
            # Verifica quali colonne esistono
            if debug:
                self.stdout.write(f"Colonne disponibili: {df.columns.tolist()}")
                
            # Verifica se esiste la colonna popolazione
            if 'popolazione' in df.columns:
                # Statistiche sulla popolazione
                num_with_pop = df['popolazione'].count()
                avg_pop = df['popolazione'].mean()
                missing_pop = df['popolazione'].isna().sum()
                
                self.stdout.write(f"Comuni con dati demografici: {num_with_pop}")
                self.stdout.write(f"Popolazione media: {avg_pop:.1f}")
                self.stdout.write(f"Comuni senza popolazione: {missing_pop}")
                self.update_progress(20, f"Trovati {num_with_pop} comuni con dati demografici")
            else:
                self.stdout.write(self.style.WARNING("Colonna 'popolazione' non trovata nei dati"))
                self.update_progress(20, "Dati demografici non trovati. Utilizzo valori predefiniti.")
            
            # Rinomina le colonne per adattarle al modello
            colonne_mappate = {
                'nome': 'Comune',
                'sigla': 'SiglaProvincia',
                'provincia': 'Provincia',
                'regione': 'Regione',
                'popolazione': 'Popolazione'  # Questa colonna esiste nel dataset
            }
            
            # Rinomina solo le colonne che esistono
            for old_col, new_col in colonne_mappate.items():
                if old_col in df.columns:
                    df = df.rename(columns={old_col: new_col})
                elif debug:
                    self.stdout.write(f"Colonna '{old_col}' non trovata nei dati")
            
            # Assicurati che tutte le colonne necessarie esistano
            required_cols = ['Comune', 'Provincia', 'Regione', 'Popolazione']
            for col in required_cols:
                if col not in df.columns:
                    if col == 'Popolazione':
                        df[col] = 0  # Default a 0 se non c'è popolazione
                    else:
                        df[col] = ''  # Default a stringa vuota per campi di testo
            
            # Converte la popolazione a interi
            df['Popolazione'] = df['Popolazione'].fillna(0).astype(int)
            
            # Aggiorna il progresso prima dell'importazione
            self.update_progress(25, "Preparazione importazione...")
            
            # Importa nel database
            total_comuni = len(df)
            self.stdout.write(f"Avvio importazione di {total_comuni} comuni...")
            self.update_progress(30, f"Avvio importazione di {total_comuni} comuni...")
            
            count = 0
            for _, row in df.iterrows():
                try:
                    Municipality.objects.create(
                        name=row['Comune'],
                        province=row['Provincia'],
                        region=row['Regione'],
                        population=row['Popolazione']
                        # ev_adoption_rate rimane al valore predefinito 2.0
                    )
                    count += 1
                    
                    # Calcola percentuale di avanzamento
                    progress = int((count / total_comuni) * 100)
                    
                    # Aggiorna la progress bar ogni 100 comuni o ogni percentuale
                    if count % 100 == 0 or progress % 5 == 0:
                        # Calcoliamo il progresso totale: 30% (pre-import) + 65% * percentuale_importazione
                        total_progress = 30 + int((progress / 100) * 65)
                        # Nel ciclo di importazione, quando aggiorni il progresso:
                        self.update_progress(
                            total_progress, 
                            f"Importati {count}/{total_comuni} comuni... ({progress}%)", 
                            current_count=count, 
                            total_count=total_comuni
                        )
                        self.stdout.write(f"Importati {count}/{total_comuni} comuni... ({progress}%)")
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Errore importazione comune {row['Comune']}: {str(e)}"))
                    
            # Controlla quanti comuni hanno popolazione 0
            zero_pop = len(df[df['Popolazione'] == 0])
            if zero_pop > 0:
                self.stdout.write(self.style.WARNING(f"{zero_pop} comuni senza dati demografici (popolazione = 0)"))
                
            self.stdout.write(self.style.SUCCESS(f'Importati con successo {count} comuni italiani'))
            self.update_progress(95, f'Importati con successo {count} comuni italiani')
            
            # Completamento finale
            self.update_progress(100, f'Importazione completata! {count} comuni importati.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Errore durante lo scaricamento dei dati: {str(e)}"))
            self.update_progress(30, f"Errore durante lo scaricamento dei dati: {str(e)}")
            
            # In caso di fallimento totale, prova con la fonte ISTAT originale
            self.stdout.write("Tentativo con fonte ISTAT originale...")
            self.update_progress(35, "Tentativo con fonte ISTAT originale...")
            self.istat_fallback()
            
    def istat_fallback(self):
        """
        Metodo di fallback usando i dati ISTAT originali
        """
        self.update_progress(40, "Download dati ISTAT in corso...")
        url_comuni = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
        
        try:
            # Scarica i dati dei comuni
            response_comuni = requests.get(url_comuni)
            response_comuni.raise_for_status()
            
            # Leggi i dati come DataFrame, gestendo la codifica corretta
            self.update_progress(45, "Processamento dati ISTAT...")
            df_comuni = pd.read_csv(StringIO(response_comuni.content.decode('latin1')), sep=';')
            
            # Rinomina le colonne per chiarezza
            colonne_mappate = {
                'Denominazione in italiano': 'Comune',
                'Denominazione dell\'Unità territoriale sovracomunale \n(valida a fini statistici)': 'Provincia',
                'Denominazione Regione': 'Regione',
                'Codice Comune formato alfanumerico': 'Codice_Comune'
            }
            
            df_comuni = df_comuni.rename(columns=colonne_mappate)
            df_comuni['Popolazione'] = 0  # Impostato a 0 poiché non ci sono dati demografici
            
            # Seleziona solo le colonne necessarie
            df_finale = df_comuni[['Comune', 'Provincia', 'Regione', 'Popolazione']]
            
            # Importa nel database
            total_comuni = len(df_finale)
            self.stdout.write(f"Avvio importazione di {total_comuni} comuni (metodo fallback)...")
            self.update_progress(50, f"Avvio importazione di {total_comuni} comuni (metodo fallback)...")
            
            count = 0
            for _, row in df_finale.iterrows():
                Municipality.objects.create(
                    name=row['Comune'],
                    province=row['Provincia'],
                    region=row.get('Regione', ''),
                    population=0  # Popolazione 0 per tutti i comuni dal metodo fallback
                )
                count += 1
                
                # Aggiorna il progresso ogni 100 comuni
                if count % 100 == 0:
                    progress = int((count / total_comuni) * 100)
                    total_progress = 50 + int((progress / 100) * 45)  # Dal 50% al 95%
                    self.update_progress(total_progress, f"Importati {count}/{total_comuni} comuni...")
                    self.stdout.write(f"Importati {count}/{total_comuni} comuni...")
                    
            self.stdout.write(self.style.WARNING(f'Importati {count} comuni italiani senza dati demografici'))
            self.update_progress(100, f'Importati {count} comuni italiani senza dati demografici')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Importazione fallita completamente: {str(e)}"))
            self.update_progress(100, f"Importazione fallita: {str(e)}")
            return None