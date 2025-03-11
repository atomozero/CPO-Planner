import requests
import random
from decimal import Decimal
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from .models import PunData, EnergyPriceProjection, GlobalSettings
from django.db import models

logger = logging.getLogger(__name__)

class PunDataService:
    """Servizio per la gestione dei dati PUN (Prezzo Unico Nazionale)"""
    
    GME_API_BASE_URL = "https://www.mercatoelettrico.org/it/WebService/MGP_Prezzi.asmx"
    
    @staticmethod
    def download_pun_data(start_date=None, end_date=None):
        """
        Scarica i dati PUN dal portale GME.
        
        Args:
            start_date: Data di inizio (datetime.date), default 7 giorni fa
            end_date: Data di fine (datetime.date), default oggi
            
        Returns:
            bool: True se il download è avvenuto con successo, False altrimenti
        """
        try:
            if not start_date:
                start_date = (datetime.now() - timedelta(days=7)).date()
            if not end_date:
                end_date = datetime.now().date()
                
            # In un ambiente reale, qui dovremmo fare chiamate API al servizio GME
            # Esempio di implementazione simulata per test
            logger.info(f"Downloading PUN data from {start_date} to {end_date}")
            
            # Simula il download per test (in produzione questo verrebbe sostituito con chiamate API reali)
            # NOTA: In un ambiente di produzione, questa funzione dovrebbe usare l'API GME
            # o scaricare i dati dal loro portale
            fake_data = PunDataService._generate_test_data(start_date, end_date)
            
            # Salva i dati nel database
            saved_count = 0
            for data_item in fake_data:
                obj, created = PunData.objects.update_or_create(
                    date=data_item['date'],
                    hour=data_item['hour'],
                    zone=data_item['zone'],
                    defaults={
                        'price': data_item['price'],
                        'timeband': data_item['timeband']
                    }
                )
                if created:
                    saved_count += 1
                    
            logger.info(f"Saved {saved_count} new PUN data entries")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading PUN data: {e}")
            return False
    
    @staticmethod
    def generate_projections(months_ahead=12):
        """
        Genera proiezioni del PUN per i prossimi mesi basandosi sui dati storici
        e applicando il tasso di inflazione.
        
        Args:
            months_ahead: Numero di mesi per cui generare proiezioni
            
        Returns:
            bool: True se la generazione è avvenuta con successo, False altrimenti
        """
        try:
            # Ottieni impostazioni globali per il tasso di inflazione
            settings = GlobalSettings.get_active()
            inflation_rate = float(settings.inflation_rate)
            
            # Ottieni ultimi 3 mesi di dati come base
            today = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=90)).date()
            
            # Calcola medie per fascia oraria
            pun_data = PunData.objects.filter(date__gte=start_date)
            
            # Se non ci sono abbastanza dati, genera dati di test
            if pun_data.count() < 100:
                PunDataService.download_pun_data(
                    start_date=start_date,
                    end_date=today
                )
                pun_data = PunData.objects.filter(date__gte=start_date)
            
            # Calcola medie per fascia
            f1_avg = pun_data.filter(timeband='F1').aggregate(avg=models.Avg('price'))['avg'] or Decimal('250.0')
            f2_avg = pun_data.filter(timeband='F2').aggregate(avg=models.Avg('price'))['avg'] or Decimal('230.0')
            f3_avg = pun_data.filter(timeband='F3').aggregate(avg=models.Avg('price'))['avg'] or Decimal('200.0')
            
            # Converti da €/MWh a €/kWh
            f1_avg_kwh = f1_avg / 1000
            f2_avg_kwh = f2_avg / 1000
            f3_avg_kwh = f3_avg / 1000
            
            # Calcola media generale
            avg_price_kwh = (f1_avg_kwh + f2_avg_kwh + f3_avg_kwh) / 3
            
            # Genera proiezioni per i mesi futuri
            current_year = today.year
            current_month = today.month
            
            for i in range(months_ahead):
                # Calcola mese e anno target
                target_month = ((current_month + i) % 12) or 12  # Assicura che sia tra 1-12
                target_year = current_year + ((current_month + i - 1) // 12)
                
                # Applica inflazione mensile 
                # Formula: prezzo * (1 + tasso_inflazione/100/12)^numero_mesi
                inflation_factor = (1 + inflation_rate/100/12) ** i
                
                projected_f1 = f1_avg_kwh * Decimal(str(inflation_factor))
                projected_f2 = f2_avg_kwh * Decimal(str(inflation_factor))
                projected_f3 = f3_avg_kwh * Decimal(str(inflation_factor))
                projected_avg = avg_price_kwh * Decimal(str(inflation_factor))
                
                # Salva la proiezione
                EnergyPriceProjection.objects.update_or_create(
                    year=target_year,
                    month=target_month,
                    defaults={
                        'f1_price': projected_f1.quantize(Decimal('0.0001')),
                        'f2_price': projected_f2.quantize(Decimal('0.0001')),
                        'f3_price': projected_f3.quantize(Decimal('0.0001')),
                        'avg_price': projected_avg.quantize(Decimal('0.0001')),
                        'inflation_rate': inflation_rate,
                        'base_period_start': start_date,
                        'base_period_end': today
                    }
                )
            
            logger.info(f"Generated {months_ahead} months of PUN projections")
            return True
            
        except Exception as e:
            logger.error(f"Error generating PUN projections: {e}")
            return False
    
    @staticmethod
    def _generate_test_data(start_date, end_date):
        """
        Genera dati PUN di test per sviluppo e debugging.
        
        Args:
            start_date: Data di inizio 
            end_date: Data di fine
            
        Returns:
            list: Lista di dizionari con dati PUN simulati
        """
        import random
        
        data = []
        current_date = start_date
        
        # Prezzi base per fasce (€/MWh)
        base_prices = {
            'F1': 280.0,  # Ore di punta più costose
            'F2': 250.0,  # Ore intermedie
            'F3': 200.0,  # Ore fuori punta più economiche
        }
        
        # Fluttuazione casuale (±15%)
        def add_fluctuation(base):
            fluctuation = random.uniform(-0.15, 0.15)
            return base * (1 + fluctuation)
        
        # Zone di mercato
        zones = ["NORD", "CNOR", "CSUD", "SUD", "SICI", "SARD"]
        
        while current_date <= end_date:
            for hour in range(24):
                # Determina la fascia oraria
                timeband = PunData.get_timeband(current_date, hour)
                
                # Genera prezzo con fluttuazione
                base_price = base_prices[timeband]
                
                # Aggiungi variazione stagionale/settimanale
                day_of_week = current_date.weekday()
                month = current_date.month
                
                # Incrementa prezzo in inverno (più alto) e estate (aria condizionata)
                if month in [1, 2, 12]:  # Inverno
                    seasonal_factor = 1.1
                elif month in [6, 7, 8]:  # Estate
                    seasonal_factor = 1.05
                else:
                    seasonal_factor = 1.0
                
                # Prezzi più bassi nel weekend
                if day_of_week >= 5:  # Sabato e domenica
                    weekday_factor = 0.9
                else:
                    weekday_factor = 1.0
                
                # Prezzo orario variabile con picco alle 18-20
                hour_factor = 1.0
                if 7 <= hour <= 9:  # Picco mattutino
                    hour_factor = 1.1
                elif 17 <= hour <= 20:  # Picco serale
                    hour_factor = 1.15
                elif 2 <= hour <= 5:  # Notte profonda
                    hour_factor = 0.85
                
                for zone in zones:
                    final_price = base_price * seasonal_factor * weekday_factor * hour_factor
                    final_price = add_fluctuation(final_price)
                    
                    # Aggiungi variazione per zone
                    if zone == "SICI":  # Sicilia spesso ha prezzi più alti
                        zone_factor = 1.08
                    elif zone == "SARD":  # Sardegna pure
                        zone_factor = 1.05
                    elif zone == "SUD":  # Sud potrebbe avere prezzi più bassi
                        zone_factor = 0.98
                    else:
                        zone_factor = 1.0
                    
                    final_price *= zone_factor
                    
                    data.append({
                        'date': current_date,
                        'hour': hour,
                        'zone': zone,
                        'price': round(final_price, 4),
                        'timeband': timeband
                    })
            
            current_date += timedelta(days=1)
        
        return data