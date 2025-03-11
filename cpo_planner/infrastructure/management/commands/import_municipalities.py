import os
import pandas as pd
from io import StringIO
import numpy as np
import requests  # Importiamo requests a livello globale
from django.core.management.base import BaseCommand
from django.conf import settings
from infrastructure.models import Municipality  # Adatta questa importazione al tuo modello effettivo

class Command(BaseCommand):
    help = 'Scarica e importa comuni italiani con popolazione nel database'
    
    """
    Comando per l'importazione della lista dei comuni italiani con dati demografici reali.
    
    Fonti dati:
    1. Lista comuni: ISTAT "Elenco-comuni-italiani.csv"
       URL: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.csv
       
    2. Dati demografici: GeoJSON OpenPolis 2021
       URL: https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_municipalities_2021.geojson
       Fonte originale: ISTAT, Censimento 2021
       
    3. Fonte alternativa: GitHub - comunijson
       URL: https://raw.githubusercontent.com/matteocontrini/comuni-json/master/comuni.json
    """

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
            # Numero totale di comuni da importare
            total_comuni = len(df)
            self.stdout.write(f"Avvio importazione di {total_comuni} comuni...")
            
            # Importa nel database
            count = 0
            for _, row in df.iterrows():
                Municipality.objects.create(
                    name=row['Comune'],
                    province=row['Provincia'],
                    region=row.get('Regione', ''),  # Aggiungiamo anche la regione
                    population=int(row.get('Popolazione', 0))
                    # ev_adoption_rate rimane al valore predefinito 2.0
                )
                count += 1
                
                # Calcola percentuale di avanzamento
                progress = int((count / total_comuni) * 100)
                
                # Mostra progresso ogni 100 comuni o ogni percentuale
                if count % 100 == 0 or progress % 5 == 0:
                    self.stdout.write(f"Importati {count}/{total_comuni} comuni... ({progress}%)")
                    
                # Se stai usando la sessione per tracciare il progresso (come nella vista RunImportView)
                # potresti aggiornare qui il progresso, ma questo richiede modifiche più profonde
                
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
            
            # Scarica dati demografici reali
            self.stdout.write("Scaricamento dati demografici reali...")
            try:
                # URL per i dati demografici ISTAT (ultimo censimento)
                url_demografia = "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2023/Elenco-codici-statistici-e-denominazioni-delle-unità-territoriali.zip"
                
                # Se il download ISTAT non funziona, utilizziamo un dataset su GitHub con dati del 2021
                url_demografia_alt = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_municipalities_2021.geojson"
                
                # Proviamo prima con dataset GitHub che è più affidabile
                self.stdout.write("Download dati demografici da GitHub...")
                try:
                    import json
                    
                    response = requests.get(url_demografia_alt)
                    response.raise_for_status()
                    
                    data = response.json()
                    popolazione_comuni = {}
                    
                    # Estrai dati demografici
                    for feature in data['features']:
                        properties = feature['properties']
                        nome = properties.get('name')
                        popolazione = properties.get('population')
                        
                        if nome and popolazione:
                            popolazione_comuni[nome] = int(popolazione)
                    
                    # Applica i dati demografici al dataframe
                    def get_popolazione(comune):
                        return popolazione_comuni.get(comune, 5000)  # Valore default se non trovato
                    
                    df_comuni['Popolazione'] = df_comuni['Comune'].apply(get_popolazione)
                    self.stdout.write(f"Dati demografici caricati con successo per {len(popolazione_comuni)} comuni")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Errore nei dati demografici: {e}"))
                    self.stdout.write("Usati valori demografici stimati (10000 abitanti)")
                    df_comuni['Popolazione'] = 10000  # valore di default
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Errore nel download dei dati demografici: {e}"))
                self.stdout.write("Usati valori demografici stimati (10000 abitanti)")
                df_comuni['Popolazione'] = 10000  # valore di default
            
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
                
                # Scarica dati demografici reali anche per il metodo alternativo
                try:
                    # Utilizziamo lo stesso dataset di GitHub usato sopra
                    url_demografia_alt = "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_municipalities_2021.geojson"
                    
                    self.stdout.write("Download dati demografici da GitHub (metodo alternativo)...")
                    
                    response_demo = requests.get(url_demografia_alt)
                    response_demo.raise_for_status()
                    
                    data = response_demo.json()
                    popolazione_comuni = {}
                    
                    # Estrai dati demografici
                    for feature in data['features']:
                        properties = feature['properties']
                        nome = properties.get('name')
                        popolazione = properties.get('population')
                        
                        if nome and popolazione:
                            popolazione_comuni[nome] = int(popolazione)
                    
                    # Applica i dati demografici al dataframe
                    def get_popolazione(comune):
                        return popolazione_comuni.get(comune, 5000)  # Valore default se non trovato
                    
                    df_alt['popolazione'] = df_alt['nome'].apply(get_popolazione)
                    self.stdout.write(f"Dati demografici caricati con successo per {len(popolazione_comuni)} comuni (metodo alternativo)")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Errore nei dati demografici alternativi: {e}"))
                    self.stdout.write("Usati valori demografici stimati (10000 abitanti)")
                    df_alt['popolazione'] = 10000  # valore di default
                
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