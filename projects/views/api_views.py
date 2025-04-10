# projects/views/api_views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET
from infrastructure.models import StationUsageProfile
import logging

# Configura il logger
logger = logging.getLogger(__name__)

# Flag per controllare il livello di dettaglio dei log
VERBOSE_LOGGING = False

@require_GET
def usage_profile_detail(request, profile_id):
    """API endpoint per ottenere i dettagli di un profilo di utilizzo"""
    try:
        # Ottieni il profilo dal database
        profile = StationUsageProfile.objects.get(pk=profile_id)
        
        if VERBOSE_LOGGING:
            logger.info(f"Profilo ID {profile_id} trovato nel database: {profile.name}")
        
        # Mappa i campi del modello StationUsageProfile ai nomi usati nel calcolo
        daily_usage_hours = calculate_daily_usage_hours(profile)
        avg_session_kwh = float(profile.avg_energy_per_session)
        utilization_rate = calculate_utilization_rate(profile)
        
        # Crea un dizionario con i dati del profilo
        profile_data = {
            'id': profile.id,
            'name': profile.name,
            'daily_usage_hours': daily_usage_hours,
            'avg_session_kwh': avg_session_kwh,
            'utilization_rate': utilization_rate,
            'suggested_price_kwh': 0.45,
            'location_type': map_customer_profile_to_location_type(profile.customer_profile),
            'source': 'database'
        }
        
        return JsonResponse(profile_data)
    except StationUsageProfile.DoesNotExist:
        # Log dell'errore solo in caso di fallback
        logger.warning(f"Profilo ID {profile_id} non trovato nel database. Utilizzando fallback.")
        
        # Restituisci un profilo fallback
        fallback_data = get_fallback_profile(profile_id)
        return JsonResponse(fallback_data)
    except Exception as e:
        # Log degli errori generici
        logger.error(f"Errore nel recupero del profilo {profile_id}: {str(e)}")
        
        # In caso di errore, restituisci un profilo di fallback
        fallback_data = get_fallback_profile(profile_id)
        return JsonResponse(fallback_data, status=200)

@require_GET
def test_revenue_calculation(request):
    """API endpoint per testare il calcolo dei ricavi attesi"""
    try:
        # Prendi i parametri dalla richiesta
        profile_id = request.GET.get('profile_id')
        power = float(request.GET.get('power', 22))
        num_connectors = int(request.GET.get('connectors', 2))
        num_chargers = int(request.GET.get('chargers', 1))
        market_day = request.GET.get('market_day', '') == 'true'
        festival_days = int(request.GET.get('festival_days', 0))
        rainy_days = int(request.GET.get('rainy_days', 0))
        
        # Ottieni i dati del profilo
        try:
            profile = StationUsageProfile.objects.get(pk=profile_id)
            
            if VERBOSE_LOGGING:
                logger.info(f"Test calcolo: Profilo {profile_id} trovato nel database: {profile.name}")
            
            # Mappa i campi come nella funzione usage_profile_detail
            daily_usage_hours = calculate_daily_usage_hours(profile)
            avg_session_kwh = float(profile.avg_energy_per_session)
            utilization_rate = calculate_utilization_rate(profile)
            location_type = map_customer_profile_to_location_type(profile.customer_profile)
            price_per_kwh = 0.45
            
            profile_data = {
                'id': profile.id,
                'name': profile.name,
                'daily_usage_hours': daily_usage_hours,
                'avg_session_kwh': avg_session_kwh,
                'utilization_rate': utilization_rate,
                'price_per_kwh': price_per_kwh,
                'location_type': location_type,
                'source': 'database'
            }
        except StationUsageProfile.DoesNotExist:
            # Log dell'errore solo in caso di fallback
            logger.warning(f"Test calcolo: Profilo {profile_id} non trovato nel database. Utilizzando fallback.")
            
            fallback = get_fallback_profile(profile_id)
            profile_data = fallback
        
        # Fattore posizione
        location_factors = {
            'city_center': 1.2,
            'commercial': 1.5,
            'suburban': 0.9,
            'highway': 1.8,
            'rural': 1.0
        }
        location_factor = location_factors.get(profile_data['location_type'], 1.0)
        
        # Calcolo sessioni
        sessions_per_day_per_connector = profile_data['daily_usage_hours'] / (profile_data['avg_session_kwh'] / power) * profile_data['utilization_rate']
        total_daily_sessions = sessions_per_day_per_connector * num_connectors * num_chargers
        
        # Calcolo kWh e ricavi giornalieri
        daily_kwh = total_daily_sessions * profile_data['avg_session_kwh']
        daily_revenue = daily_kwh * profile_data['price_per_kwh'] * location_factor
        
        # Fattore disponibilità
        market_days = 52 if market_day else 0
        unavailable_days = market_days + festival_days
        available_days = 365 - unavailable_days
        rainy_impact = rainy_days * 0.1
        availability_factor = (available_days - rainy_impact) / 365
        
        # Ricavi annuali
        annual_revenue = daily_revenue * 365 * availability_factor
        
        # Crea risposta dettagliata
        result = {
            'success': True,
            'profile': {
                'id': profile_data['id'],
                'name': profile_data['name'],
                'daily_usage_hours': profile_data['daily_usage_hours'],
                'avg_session_kwh': profile_data['avg_session_kwh'],
                'utilization_rate': profile_data['utilization_rate'],
                'price_per_kwh': profile_data['price_per_kwh'],
                'location_type': profile_data['location_type'],
                'location_factor': location_factor,
                'source': profile_data.get('source', 'fallback')
            },
            'station': {
                'power': power,
                'num_connectors': num_connectors,
                'num_chargers': num_chargers,
                'market_day': market_day,
                'festival_days': festival_days,
                'rainy_days': rainy_days
            },
            'calculation': {
                'sessions_per_day_per_connector': round(sessions_per_day_per_connector, 2),
                'total_daily_sessions': round(total_daily_sessions, 2),
                'daily_kwh': round(daily_kwh, 2),
                'daily_revenue': round(daily_revenue, 2),
                'unavailable_days': unavailable_days,
                'rainy_impact': round(rainy_impact, 2),
                'availability_factor': round(availability_factor, 4),
                'annual_revenue': round(annual_revenue, 2)
            }
        }
        
        return JsonResponse(result)
    except Exception as e:
        # Log sempre gli errori generici 
        logger.error(f"Errore nel test del calcolo ricavi: {str(e)}")
        
        return JsonResponse({
            'success': False,
            'error': str(e),
            'source': 'error'
        }, status=500)

# Funzioni di supporto per mappare i dati del modello agli attributi necessari per il calcolo

def calculate_daily_usage_hours(profile):
    """
    Calcola le ore di utilizzo giornaliere basandosi sui dati del profilo.
    Prende la media ponderata degli utilizzi nei giorni feriali e nei weekend.
    """
    # Calcola la media ponderata dell'utilizzo giornaliero
    # Considera 5 giorni feriali e 2 giorni weekend
    weekday_avg = (profile.weekday_morning_usage + profile.weekday_afternoon_usage + profile.weekday_evening_usage) / 3
    weekend_avg = (profile.weekend_morning_usage + profile.weekend_afternoon_usage + profile.weekend_evening_usage) / 3
    
    # Normalizza le percentuali in ore (assumendo 24 ore max)
    weekday_hours = (weekday_avg / 100) * 12  # Assumiamo un massimo di 12 ore attive al giorno
    weekend_hours = (weekend_avg / 100) * 12
    
    # Media ponderata (5 giorni feriali, 2 giorni weekend)
    daily_usage_hours = (weekday_hours * 5 + weekend_hours * 2) / 7
    
    return round(daily_usage_hours, 1)

def calculate_utilization_rate(profile):
    """
    Calcola il tasso di utilizzo basandosi sui dati del profilo.
    """
    # Se il profilo ha un campo avg_daily_sessions, possiamo usare quello
    # per calcolare il tasso di utilizzo
    if hasattr(profile, 'avg_daily_sessions') and profile.avg_daily_sessions:
        # Assumiamo che 24 sessioni/giorno sia il massimo (1 ogni ora)
        # e che quindi corrisponda a un tasso di utilizzo del 100%
        max_sessions = 24
        utilization_rate = min(float(profile.avg_daily_sessions) / max_sessions, 1.0)
    else:
        # Altrimenti usiamo un valore basato sul tipo di cliente
        customer_profile_rates = {
            'commuter': 0.6,
            'resident': 0.4,
            'visitor': 0.7,
            'business': 0.5,
            'mixed': 0.5
        }
        utilization_rate = customer_profile_rates.get(profile.customer_profile, 0.5)
    
    return round(utilization_rate, 2)

def map_customer_profile_to_location_type(customer_profile):
    """
    Mappa il tipo di cliente a un tipo di posizione.
    """
    mapping = {
        'commuter': 'city_center',
        'resident': 'suburban',
        'visitor': 'commercial',
        'business': 'commercial',
        'mixed': 'city_center'
    }
    return mapping.get(customer_profile, 'city_center')

def get_fallback_profile(profile_id):
    """
    Restituisce un profilo di fallback quando non è possibile recuperare un profilo dal database.
    """
    # Dati predefiniti per i profili di utilizzo di fallback
    DEFAULT_PROFILES = {
        "1": {
            'id': 1,
            'name': 'Parcheggio centrale (fallback)',
            'daily_usage_hours': 7.0,
            'avg_session_kwh': 15.0,
            'utilization_rate': 0.5,
            'suggested_price_kwh': 0.45,
            'location_type': 'city_center',
            'source': 'fallback'
        },
        "2": {
            'id': 2,
            'name': 'Parcheggio periferico (fallback)',
            'daily_usage_hours': 6.0,
            'avg_session_kwh': 18.0,
            'utilization_rate': 0.4,
            'suggested_price_kwh': 0.40,
            'location_type': 'suburban',
            'source': 'fallback'
        },
        "3": {
            'id': 3,
            'name': 'Centro commerciale (fallback)',
            'daily_usage_hours': 10.0,
            'avg_session_kwh': 20.0,
            'utilization_rate': 0.7,
            'suggested_price_kwh': 0.50,
            'location_type': 'commercial',
            'source': 'fallback'
        },
        "4": {
            'id': 4,
            'name': 'Strada urbana (fallback)',
            'daily_usage_hours': 8.0,
            'avg_session_kwh': 15.0,
            'utilization_rate': 0.6,
            'suggested_price_kwh': 0.45,
            'location_type': 'city_center',
            'source': 'fallback'
        },
        "5": {
            'id': 5,
            'name': 'Autostrada/Superstrada (fallback)',
            'daily_usage_hours': 12.0,
            'avg_session_kwh': 25.0,
            'utilization_rate': 0.8,
            'suggested_price_kwh': 0.55,
            'location_type': 'highway',
            'source': 'fallback'
        }
    }
    
    profile_key = str(profile_id)
    if profile_key in DEFAULT_PROFILES:
        return DEFAULT_PROFILES[profile_key]
    else:
        # Se il profilo richiesto non esiste neanche tra i fallback, restituisci un profilo generico
        return {
            'id': int(profile_id) if profile_id else 0,
            'name': f'Profilo generico {profile_id} (fallback)',
            'daily_usage_hours': 8.0,
            'avg_session_kwh': 18.0,
            'utilization_rate': 0.5,
            'suggested_price_kwh': 0.45,
            'location_type': 'city_center',
            'source': 'fallback'
        }