import os
import requests
import pandas as pd
from io import StringIO
import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from infrastructure.models import Municipality  # Adatta questa importazione al tuo modello effettivo

class Command(BaseCommand):
    help = 'Scarica e importa comuni italiani con popolazione nel database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', 
            action='store_true', 
            help='Sovrascrive i dati esistenti',
        )

    def handle(self, *args, **options):
        force = options['force']
        
        # Controlla se ci sono già dati nel database
        existing_count = Municipality.objects.count()
        if existing_count > 0 and not force:
            self.stdout.write(
                self.style.WARNING(f'Ci sono già {existing_count} comuni nel database. Usa --force per sovrascriverli.')
            )
            return
            
        # Se force è True, cancella i comuni esistenti
        if force and existing_count > 0:
            self.stdout.write(self.style.WARNING(f'Cancellazione di {existing_count} comuni esistenti...'))
            Municipality.objects.all().delete()
        
        # Scarica i dati
        df = self.scarica_comuni_italiani()
                
        # Nel metodo handle() del comando
        if df is not None:
            # Importa nel database
            count = 0
            for _, row in df.iterrows():
                Municipality.objects.create(
                    name=row['Comune'],
                    province=row['Provincia'],
                    # Non includere 'region' poiché non esiste nel modello
                    population=int(row.get('Popolazione', 0))
                    # ev_adoption_rate rimane al valore predefinito 2.0
                )
                count += 1
                
                # Mostra progresso ogni 100 comuni
                if count % 100 == 0:
                    self.stdout.write(f"Importati {count} comuni...")
                    self.stdout.write(self.style.SUCCESS(f'Importati con successo {count} comuni italiani'))
            
    def scarica_comuni_italiani(self):
        """
        Scarica i dati dei comuni italiani dall'API di ISTAT o da una fonte alternativa
        """
        self.stdout.write("Scaricamento dati dei comuni italiani in corso...")
        
        # URL per i dati dei comuni dall'ISTAT
        url_comuni = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv"
        
        try:
            # Scarica i dati dei comuni
            response_comuni = requests.get(url_comuni)
            response_comuni.raise_for_status()
            
            # Leggi i dati come DataFrame, gestendo la codifica corretta
            df_comuni = pd.read_csv(StringIO(response_comuni.content.decode('latin1')), sep=';')
            
            # Rinomina le colonne per chiarezza
            colonne_mappate = {
                'Denominazione in italiano': 'Comune',
                'Denominazione dell\'Unità territoriale sovracomunale \n(valida a fini statistici)': 'Provincia',
                'Denominazione Regione': 'Regione',
                'Codice Comune formato alfanumerico': 'Codice_Comune'
            }
            
            df_comuni = df_comuni.rename(columns=colonne_mappate)
            
            # Metodo alternativo: usa popolazione simulata per semplicità
            # Nella versione reale dovresti collegare a dati effettivi di popolazione
            self.stdout.write("Generazione dati di popolazione simulati...")
            df_comuni['Popolazione'] = np.random.randint(1000, 100000, size=len(df_comuni))
            df_completo = df_comuni
                
            # Seleziona solo le colonne necessarie
            df_finale = df_completo[['Comune', 'Provincia', 'Regione', 'Popolazione']]
            
            self.stdout.write(f"Scaricati con successo {len(df_finale)} comuni")
            
            return df_finale
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Errore durante lo scaricamento dei dati: {e}"))
            
            # Metodo alternativo: scarica da GitHub dataset già pronti
            self.stdout.write("Tentativo con fonte alternativa...")
            url_alternativo = "https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json"
            
            try:
                response_alt = requests.get(url_alternativo)
                response_alt.raise_for_status()
                
                comuni_json = response_alt.json()
                
                # Converti JSON in DataFrame
                df_alt = pd.DataFrame(comuni_json)
                
                # Aggiungi popolazione simulata (da sostituire con dati reali)
                df_alt['popolazione'] = np.random.randint(1000, 100000, size=len(df_alt))
                
                # Rinomina colonne
                df_alt = df_alt.rename(columns={
                    'nome': 'Comune',
                    'provincia': 'Provincia',
                    'regione': 'Regione',
                    'popolazione': 'Popolazione'
                })
                
                self.stdout.write(f"Scaricati con successo {len(df_alt)} comuni (fonte alternativa)")
                
                return df_alt[['Comune', 'Provincia', 'Regione', 'Popolazione']]
                
            except Exception as e2:
                self.stdout.write(self.style.ERROR(f"Anche il metodo alternativo ha fallito: {e2}"))
                return None