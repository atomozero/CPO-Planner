# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.http import JsonResponse
from datetime import datetime, timedelta
from django.db import models
from django.utils.translation import gettext_lazy as _

# Mantieni i modelli specifici dell'infrastruttura fino alla consolidazione completa
from .models import (
    ChargingProject, ChargingStation, ProjectTask,
    ElectricityTariff, ManagementFee, StationUsageProfile, ChargingStationTemplate,
    GlobalSettings, PunData, EnergyPriceProjection
)
from .forms import (
    MunicipalityForm, ChargingProjectForm, ChargingStationForm, ProjectTaskForm,
    ElectricityTariffForm, ManagementFeeForm, StationUsageProfileForm, ChargingStationTemplateForm,
    GlobalSettingsForm, EnergyPriceProjectionForm
)
from .services import PunDataService

from django.http import HttpResponse
from .reports import MunicipalityReportGenerator, ChargingProjectReportGenerator, ChargingStationSheetGenerator

from django.urls import reverse
from django.views.generic import View
from django.core.management import call_command

from django.http import JsonResponse
from django.db.models import Avg, Count, Sum

# Importazioni aggiuntive per WeasyPrint
from django.template.loader import render_to_string
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

from django.conf import settings

# Viste per i Comuni
from infrastructure.models import Municipality
from cpo_core.models import Project, SubProject
from cpo_core.models.subproject import Charger

class ChargingStationTemplatePrintPDFView(LoginRequiredMixin, DetailView):
    model = ChargingStationTemplate
    
    def get(self, request, *args, **kwargs):
        template = self.get_object()
        
        # Calcola il costo totale
        total_cost = template.calculate_total_cost()
        
        # Recupera dati aggiuntivi (come nella vista originale)
        annual_cost = template.calculate_annual_cost()
        
        # Ottieni eventuale tariffa elettrica e profilo di utilizzo attivi
        active_tariff = ElectricityTariff.objects.filter(active=True).first()
        default_profile = StationUsageProfile.objects.first()
        
        monthly_energy_cost = 0
        monthly_fixed_cost = 0
        monthly_total_cost = 0
        annual_operating_cost = 0
        
        # Calcola i costi operativi stimati se sono disponibili la tariffa e il profilo
        if active_tariff and default_profile:
            monthly_kwh = default_profile.calculate_monthly_usage(template.power_kw)
            
            # Determina il costo in base alla potenza
            if template.power_kw <= 7:
                kwh_cost = float(active_tariff.cost_tier1)
            elif template.power_kw <= 22:
                kwh_cost = float(active_tariff.cost_tier2)
            elif template.power_kw <= 50:
                kwh_cost = float(active_tariff.cost_tier3)
            elif template.power_kw <= 150:
                kwh_cost = float(active_tariff.cost_tier4)
            else:
                kwh_cost = float(active_tariff.cost_tier5)
                
            monthly_energy_cost = monthly_kwh * kwh_cost
            monthly_fixed_cost = float(active_tariff.connection_fee) + (template.power_kw * float(active_tariff.power_fee))
            monthly_total_cost = monthly_energy_cost + monthly_fixed_cost
            annual_operating_cost = (monthly_energy_cost + monthly_fixed_cost) * 12
        
        # Prepara il contesto per il rendering del template
        context = {
            'template': template,
            'total_cost': total_cost,
            'annual_cost': annual_cost,
            'active_tariff': active_tariff,
            'usage_profile': default_profile,
            'monthly_energy_cost': monthly_energy_cost,
            'monthly_fixed_cost': monthly_fixed_cost,
            'monthly_total_cost': monthly_total_cost,
            'annual_operating_cost': annual_operating_cost,
            'current_date': datetime.now().strftime('%d/%m/%Y'),  # Data di generazione del report
        }
        
        # Renderizza l'HTML usando il template specifico per PDF
        html_string = render_to_string('infrastructure/station_template_pdf.html', context, request=request)
        
        # Converti HTML in PDF
        html = HTML(string=html_string, base_url=request.build_absolute_uri('/'))
        pdf = html.write_pdf()
        
        # Prepara la risposta
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{template.brand}_{template.model}_template.pdf"'
        
        return response
    
def municipality_autocomplete(request):
    """Fornisce funzionalità di autocompletamento per i comuni"""
    query = request.GET.get('q', '')
    municipality_id = request.GET.get('id')
    
    # Se viene fornito un ID specifico, restituisci i dettagli di quel comune
    if municipality_id:
        try:
            m = Municipality.objects.get(pk=municipality_id)
            results = [{
                'id': m.id, 
                'text': f"{m.name} ({m.province})", 
                'population': m.population,
                'logo_url': m.logo.url if m.logo else None
            }]
            return JsonResponse({'results': results})
        except Municipality.DoesNotExist:
            return JsonResponse({'results': []})
    
    # Altrimenti esegui la ricerca per nome
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Cerca comuni che iniziano con la stringa di ricerca
    municipalities = Municipality.objects.filter(
        name__istartswith=query
    ).values('id', 'name', 'province', 'population')[:10]
    
    results = []
    for m in municipalities:
        municipality = Municipality.objects.get(pk=m['id'])
        results.append({
            'id': m['id'], 
            'text': f"{m['name']} ({m['province']})", 
            'population': m['population'],
            'logo_url': municipality.logo.url if municipality.logo else None
        })
    
    return JsonResponse({'results': results})

class ImportMunicipalitiesView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Mostra la pagina con il pulsante di importazione
        total_municipalities = Municipality.objects.count()
        return render(request, 'infrastructure/import_municipalities.html', {
            'total_municipalities': total_municipalities
        })
        
    def post(self, request, *args, **kwargs):
        try:
            # Controlla se forzare l'importazione
            force = request.POST.get('force', 'false').lower() == 'true'
            
            # Redirect alla pagina che mostra la progress bar
            return redirect(reverse('infrastructure:run_import') + f'?force={force}')
            
        except Exception as e:
            messages.error(request, f"Errore durante l'importazione: {str(e)}")
            return redirect(reverse('infrastructure:municipality-list'))
        
# Vista per eseguire l'importazione in modo diretto
class RunImportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        force = request.GET.get('force', 'false').lower() == 'true'
        
        # Mostra la pagina ma esegui immediatamente l'importazione
        return render(request, 'infrastructure/run_import.html', {
            'force': force,
            'auto_start': True
        })
    
    def post(self, request, *args, **kwargs):
        # Questa chiamata verrà eseguita una sola volta per avviare l'importazione
        force = request.POST.get('force', 'false').lower() == 'true'
        
        try:
            # Esegui l'importazione direttamente (non in un thread separato)
            if force:
                call_command('import_municipalities', force=True)
            else:
                call_command('import_municipalities')
                
            # Conta i comuni dopo l'importazione
            total_municipalities = Municipality.objects.count()
            
            return JsonResponse({
                'status': 'completed',
                'progress': 100,
                'message': f'Importazione completata! {total_municipalities} comuni importati.',
                'redirect_url': reverse('infrastructure:municipality-list')
            })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f"Errore nell'importazione: {e}",
                'redirect_url': reverse('infrastructure:municipality-list')
            })

class MunicipalityListView(LoginRequiredMixin, ListView):
    model = Municipality
    context_object_name = 'municipality_list'
    template_name = 'infrastructure/municipality_list.html'

    def get_queryset(self):
        # Ottieni gli ID dei comuni coinvolti nei sottoprogetti
        municipality_ids = SubProject.objects.values_list('municipality_id', flat=True).distinct()
        
        # Restituisci solo i comuni che hanno sottoprogetti associati
        return Municipality.objects.filter(id__in=municipality_ids)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ottieni l'elenco filtrato di comuni
        municipalities = context['municipality_list']
        
        # Calcola la popolazione totale dei comuni nei progetti
        total_population = municipalities.aggregate(Sum('population'))['population__sum'] or 0
        context['total_population'] = total_population
        
        # Calcola il numero di progetti e stazioni per ogni comune
        municipality_data = {}
        for mun in municipalities:
            # Conta i sottoprogetti per questo comune
            subprojects = SubProject.objects.filter(municipality_id=mun.id)
            subproject_count = subprojects.count()
            
            # Conta le colonnine collegate ai sottoprogetti di questo comune
            charger_count = 0
            for sp in subprojects:
                charger_count += sp.chargers.count()
            
            # Salva i dati per questo comune
            municipality_data[mun.id] = {
                'projects_count': subproject_count,
                'stations_count': charger_count if charger_count > 0 else subproject_count
            }
        
        # Aggiungi questi dati al contesto
        context['municipality_data'] = municipality_data
        
        # Conta progetti attivi
        active_projects = Project.objects.count()
        context['active_projects'] = active_projects
        
        # Conta sottoprogetti (stazioni) totali
        total_stations = SubProject.objects.count()
        context['total_stations'] = total_stations
        
        # Conta colonnine totali
        total_chargers = Charger.objects.count()
        if total_chargers > 0:
            context['total_stations'] = total_chargers  # Se ci sono colonnine, mostriamo quelle piuttosto che i sottoprogetti
        
        # Dati per la distribuzione regionale
        regions = municipalities.values('region').annotate(count=Count('id')).order_by('-count')
        context['region_data'] = []
        for region in regions:
            if region['region']:  # Assicurati che ci sia un valore per la regione
                context['region_data'].append({
                    'name': region['region'],
                    'count': region['count']
                })
        
        # Top 5 comuni per stazioni/colonnine
        context['top_municipalities'] = []
        
        # Crea una lista di comuni ordinata per numero di colonnine/stazioni
        top_mun_list = []
        for mun_id, data in municipality_data.items():
            mun = Municipality.objects.get(id=mun_id)
            top_mun_list.append({
                'name': mun.name,
                'total_stations': data['stations_count']
            })
        
        # Ordina la lista e prendi i primi 5
        top_mun_list.sort(key=lambda x: x['total_stations'], reverse=True)
        context['top_municipalities'] = top_mun_list[:5]
        
        return context

class MunicipalityDetailView(LoginRequiredMixin, DetailView):
    model = Municipality
    context_object_name = 'municipality'
    template_name = 'infrastructure/municipality_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ottieni i sottoprogetti associati a questo comune usando l'ID del comune
        from cpo_core.models.subproject import SubProject
        subprojects = SubProject.objects.filter(municipality_id=self.object.id)
        
        # Ottieni i progetti associati a questi sottoprogetti
        from cpo_core.models.project import Project
        project_ids = subprojects.values_list('project_id', flat=True).distinct()
        projects = Project.objects.filter(id__in=project_ids)
        
        context['projects'] = projects
        context['subprojects'] = subprojects
        
        return context

class MunicipalityCreateView(LoginRequiredMixin, CreateView):
    model = Municipality
    form_class = MunicipalityForm
    template_name = 'municipalities/municipality_form.html'
    success_url = reverse_lazy('infrastructure:municipality-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Nuovo Comune'
        context['action'] = 'Crea'
        return context
    
    def form_valid(self, form):
        # Per prima cosa salviamo per ottenere l'ID
        response = super().form_valid(form)
        
        # Gestione esplicita dell'upload del file
        logo = self.request.FILES.get('logo')
        if logo:
            try:
                # Assicuriamo che il nome file non contenga spazi e caratteri speciali
                import os
                import shutil
                from django.utils.text import slugify
                import logging
                from django.conf import settings
                
                logger = logging.getLogger(__name__)
                logger.info(f"Ricevuto file logo: {logo.name}, size: {logo.size}")
                
                # Ottieni estensione originale del file
                filename, extension = os.path.splitext(logo.name)
                # Crea un nome file sicuro
                safe_filename = f"municipality_{form.instance.id}_{slugify(filename)}{extension}"
                
                # Percorso completo dove salvare il file
                upload_dir = os.path.join(settings.MEDIA_ROOT, "municipality_logos")
                os.makedirs(upload_dir, exist_ok=True)
                
                full_path = os.path.join(upload_dir, safe_filename)
                logger.info(f"Salvando il file in: {full_path}")
                
                # Salva manualmente il file
                with open(full_path, 'wb+') as destination:
                    for chunk in logo.chunks():
                        destination.write(chunk)
                
                # Imposta il percorso relativo nel database
                rel_path = f"municipality_logos/{safe_filename}"
                
                # Aggiorna l'istanza corrente
                form.instance.logo = rel_path
                form.instance.save()
                
                logger.info(f"Dopo il salvataggio: {form.instance.logo}")
            except Exception as e:
                import traceback
                logger.error(f"Errore nel salvataggio del logo: {e}")
                logger.error(traceback.format_exc())
            
        messages.success(self.request, f"Comune {form.instance.name} creato con successo!")
        return response
        
        
class MunicipalityUpdateView(LoginRequiredMixin, UpdateView):
    model = Municipality
    form_class = MunicipalityForm
    template_name = 'municipalities/municipality_form.html'
    success_url = reverse_lazy('infrastructure:municipality-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Modifica Comune: {self.object.name}'
        context['action'] = 'Aggiorna'
        return context
    
    def form_valid(self, form):
        # Gestione esplicita dell'upload del file prima di salvare il form
        logo = self.request.FILES.get('logo')
        
        # Prima debug del form e della request
        import json
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"POST data: {json.dumps(dict(self.request.POST))}")
        logger.info(f"Files: {self.request.FILES}")
        
        # Salva il file se esiste
        if logo:
            try:
                import os
                import shutil
                from django.utils.text import slugify
                from django.conf import settings
                
                logger.info(f"Ricevuto file logo: {logo.name}, size: {logo.size}")
                
                # Ottieni estensione originale del file
                filename, extension = os.path.splitext(logo.name)
                # Crea un nome file sicuro
                safe_filename = f"municipality_{form.instance.id}_{slugify(filename)}{extension}"

                # Percorso completo dove salvare il file
                upload_dir = os.path.join(settings.MEDIA_ROOT, "municipality_logos")
                if not os.path.exists(upload_dir):
                    os.makedirs(upload_dir)
                
                full_path = os.path.join(upload_dir, safe_filename)
                logger.info(f"Salvando il file in: {full_path}")
                
                # Prova a scrivere direttamente nel file system come test
                try:
                    with open('/home/atomozero/CPO-Planner/media/debug_file.txt', 'w') as f:
                        f.write(f"Test file creato - {logo.name}")
                    logger.info("File di debug creato con successo")
                except Exception as e:
                    logger.error(f"Errore nella creazione del file di debug: {e}")
                
                # Salva manualmente il file
                with open(full_path, 'wb+') as destination:
                    for chunk in logo.chunks():
                        destination.write(chunk)
                
                # Imposta il percorso relativo nel database
                rel_path = f"municipality_logos/{safe_filename}"
                logger.info(f"Percorso relativo: {rel_path}")
                
                # Aggiorna il form prima di salvarlo
                form.instance.logo = rel_path
                
                # Dopo il salvataggio, verifica che il file esista
                if os.path.exists(full_path):
                    logger.info(f"File salvato correttamente in {full_path}")
                else:
                    logger.error(f"File NON trovato in {full_path}")
                
            except Exception as e:
                import traceback
                logger.error(f"Errore nel salvataggio del logo: {e}")
                logger.error(traceback.format_exc())
        
        # Ora salviamo il form con il logo già impostato
        response = super().form_valid(form)
            
        messages.success(self.request, f"Comune {form.instance.name} aggiornato con successo!")
        return response
        
        
class MunicipalityDeleteView(LoginRequiredMixin, DeleteView):
    model = Municipality
    context_object_name = 'municipality'
    template_name = 'municipalities/municipality_confirm_delete.html'
    success_url = reverse_lazy('infrastructure:municipality-list')
    
    def delete(self, request, *args, **kwargs):
        municipality = self.get_object()
        messages.success(request, f"Comune {municipality.name} eliminato con successo!")
        return super().delete(request, *args, **kwargs)


from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

@login_required
def municipality_upload_logo(request, pk):
    """View speciale per l'upload diretto del logo del comune"""
    import os
    import json
    import logging
    from django.utils.text import slugify
    from django.conf import settings
    
    logger = logging.getLogger(__name__)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Solo metodo POST consentito'}, status=405)
    
    try:
        # Ottieni il comune
        municipality = Municipality.objects.get(id=pk)
        
        # Verifica se c'è un file
        if 'logo' not in request.FILES:
            return JsonResponse({'error': 'Nessun file logo inviato'}, status=400)
            
        logo = request.FILES['logo']
        logger.info(f"Ricevuto file: {logo.name}, size: {logo.size}")
        
        # Crea un nome sicuro per il file
        filename, extension = os.path.splitext(logo.name)
        safe_filename = f"municipality_{pk}_{slugify(filename)}{extension}"
        
        # Assicurati che la directory esista
        upload_dir = os.path.join(settings.MEDIA_ROOT, "municipality_logos")
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        # Salva il file
        full_path = os.path.join(upload_dir, safe_filename)
        with open(full_path, 'wb+') as destination:
            for chunk in logo.chunks():
                destination.write(chunk)
                
        # Registra che il file è stato salvato
        rel_path = f"municipality_logos/{safe_filename}"
        logger.info(f"File salvato in: {full_path}")
        logger.info(f"Percorso relativo: {rel_path}")
        
        # Aggiorna il modello
        municipality.logo = f"municipality_logos/{safe_filename}"
        municipality.save()
        
        # Verifica se il file esiste dopo il salvataggio
        if os.path.exists(full_path):
            logger.info(f"File verificato in: {full_path}")
            return JsonResponse({
                'success': True, 
                'message': 'Logo caricato con successo',
                'path': rel_path
            })
        else:
            logger.error(f"File NON trovato dopo il salvataggio: {full_path}")
            return JsonResponse({
                'error': 'File non trovato dopo il salvataggio'
            }, status=500)
            
    except Municipality.DoesNotExist:
        return JsonResponse({'error': 'Comune non trovato'}, status=404)
    except Exception as e:
        import traceback
        logger.error(f"Errore durante l'upload del logo: {e}")
        logger.error(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=500)
        
@login_required
def municipality_test_upload(request, municipality_id):
    """Visualizza una pagina di test per l'upload del logo"""
    return render(request, 'municipalities/municipality_test_upload.html', {
        'municipality_id': municipality_id
    })


@login_required
def update_municipality_coordinates(request, pk):
    """Aggiorna le coordinate di un comune via AJAX"""
    import json
    
    if request.method != 'POST' or not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Metodo non consentito'}, status=405)
    
    try:
        # Ottieni i dati dalla richiesta
        latitude = request.POST.get('latitude')
        longitude = request.POST.get('longitude')
        
        if not latitude or not longitude:
            return JsonResponse({'success': False, 'error': 'Coordinate mancanti'}, status=400)
        
        # Converti in float
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except ValueError:
            return JsonResponse({'success': False, 'error': 'Formato coordinate non valido'}, status=400)
        
        # Ottieni il comune
        municipality = Municipality.objects.get(id=pk)
        
        # Aggiorna le coordinate
        municipality.latitude = latitude
        municipality.longitude = longitude
        municipality.save()
        
        return JsonResponse({'success': True})
    
    except Municipality.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Comune non trovato'}, status=404)
    except Exception as e:
        import traceback
        print(f"Errore nell'aggiornamento delle coordinate: {e}")
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
# Viste per i Progetti
class ChargingProjectListView(LoginRequiredMixin, ListView):
    model = ChargingProject
    context_object_name = 'projects'
    template_name = 'projects/project_list.html'
    
class ChargingProjectDetailView(LoginRequiredMixin, DetailView):
    model = ChargingProject
    context_object_name = 'project'
    template_name = 'projects/project_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stations'] = self.object.charging_stations.all()
        return context

class ChargingProjectCreateView(LoginRequiredMixin, CreateView):
    model = ChargingProject
    form_class = ChargingProjectForm
    template_name = 'projects/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('infrastructure:project-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Assicurati che il campo municipality sia impostato correttamente
        municipality_id = self.request.POST.get('municipality')
        if municipality_id:
            form.instance.municipality_id = municipality_id
        
        messages.success(self.request, f"Progetto {form.instance.name} creato con successo!")
        return super().form_valid(form)
        
        
class ChargingProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = ChargingProject
    form_class = ChargingProjectForm
    template_name = 'projects/project_form.html'
    
    def get_success_url(self):
        return reverse_lazy('infrastructure:project-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        messages.success(self.request, f"Progetto {form.instance.name} aggiornato con successo!")
        return super().form_valid(form)
        
        
class ChargingProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = ChargingProject
    context_object_name = 'project'
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('infrastructure:project-list')
    
    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        messages.success(request, f"Progetto {project.name} eliminato con successo!")
        return super().delete(request, *args, **kwargs)

# Viste per le Stazioni di Ricarica
class ChargingStationListView(LoginRequiredMixin, ListView):
    model = ChargingStation
    context_object_name = 'stations'
    template_name = 'stations/station_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Sum, Count, Case, When, IntegerField
        
        # Statistiche di base
        context['active_stations'] = ChargingStation.objects.filter(status='active').count()
        context['total_power'] = ChargingStation.objects.aggregate(Sum('power_kw'))['power_kw__sum'] or 0
        context['total_projects'] = ChargingProject.objects.filter(charging_stations__isnull=False).distinct().count()
        
        # Stazioni con coordinate per la mappa
        context['stations_with_coords'] = ChargingStation.objects.filter(latitude__isnull=False, longitude__isnull=False)
        
        # Conteggi per stato
        context['status_counts'] = {
            'planned': ChargingStation.objects.filter(status='planned').count(),
            'installing': ChargingStation.objects.filter(status='installing').count(),
            'active': ChargingStation.objects.filter(status='active').count(),
            'maintenance': ChargingStation.objects.filter(status='maintenance').count(),
            'inactive': ChargingStation.objects.filter(status='inactive').count(),
        }
        
        # Distribuzione potenza
        context['power_distribution'] = [
            {'range': '0-22 kW', 'count': ChargingStation.objects.filter(power_kw__lte=22).count()},
            {'range': '23-50 kW', 'count': ChargingStation.objects.filter(power_kw__gt=22, power_kw__lte=50).count()},
            {'range': '51-100 kW', 'count': ChargingStation.objects.filter(power_kw__gt=50, power_kw__lte=100).count()},
            {'range': '101-150 kW', 'count': ChargingStation.objects.filter(power_kw__gt=100, power_kw__lte=150).count()},
            {'range': '151+ kW', 'count': ChargingStation.objects.filter(power_kw__gt=150).count()},
        ]
        
        return context
    
class ChargingStationDetailView(LoginRequiredMixin, DetailView):
    model = ChargingStation
    context_object_name = 'station'
    template_name = 'stations/station_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Puoi aggiungere qui dati simulati per le statistiche
        # Esempio:
        context['usage_percentage'] = 25  # percentuale di tempo in uso
        context['ready_percentage'] = 70  # percentuale di tempo pronta
        context['unavailable_percentage'] = 5  # percentuale di tempo non disponibile
        
        # Dati ricavi mensili (simulati)
        context['monthly_revenue'] = {
            'jan': 120, 'feb': 140, 'mar': 160, 'apr': 190,
            'may': 210, 'jun': 240, 'jul': 260, 'aug': 280,
            'sep': 250, 'oct': 220, 'nov': 180, 'dec': 150
        }
        
        return context
class ChargingStationCreateView(LoginRequiredMixin, CreateView):
    model = ChargingStation
    form_class = ChargingStationForm
    template_name = 'stations/station_form.html'
    
    def get_success_url(self):
        return reverse_lazy('station-detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        # Se il progetto è fornito nell'URL, assegniamolo alla stazione
        project_id = self.kwargs.get('project_id')
        if project_id:
            form.instance.project_id = project_id
        
        messages.success(self.request, f"Stazione di ricarica {form.instance.code} creata con successo!")
        return super().form_valid(form)



class ProjectTaskListView(LoginRequiredMixin, ListView):
    model = ProjectTask
    context_object_name = 'tasks'
    template_name = 'tasks/task_list.html'

        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        if project_id:
            context['project'] = get_object_or_404(ChargingProject, pk=project_id)
        return context

class ProjectTaskCreateView(LoginRequiredMixin, CreateView):
    model = ProjectTask
    form_class = ProjectTaskForm
    template_name = 'tasks/task_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        project_id = self.kwargs.get('project_id')
        if project_id:
            form.fields['project'].initial = project_id
            # Filtra le dipendenze solo per il progetto corrente
            form.fields['dependencies'].queryset = ProjectTask.objects.filter(project_id=project_id)
        return form
    
    def get_success_url(self):
        project_id = self.kwargs.get('project_id') or self.object.project.id
        return reverse_lazy('project-tasks', kwargs={'project_id': project_id})
    
    def form_valid(self, form):
        project_id = self.kwargs.get('project_id')
        if project_id:
            form.instance.project_id = project_id
        
        messages.success(self.request, f"Attività '{form.instance.name}' creata con successo!")
        return super().form_valid(form)

class ProjectTaskUpdateView(LoginRequiredMixin, UpdateView):
    model = ProjectTask
    form_class = ProjectTaskForm
    template_name = 'tasks/task_form.html'
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtra le dipendenze solo per il progetto corrente, escludendo se stessa
        form.fields['dependencies'].queryset = ProjectTask.objects.filter(
            project=self.object.project
        ).exclude(pk=self.object.pk)
        return form
    
    def get_success_url(self):
        return reverse_lazy('project-tasks', kwargs={'project_id': self.object.project.id})
    
    def form_valid(self, form):
        messages.success(self.request, f"Attività '{form.instance.name}' aggiornata con successo!")
        return super().form_valid(form)
    

def project_gantt_view(request, project_id):
    project = get_object_or_404(ChargingProject, pk=project_id)
    tasks = project.tasks.all()
    
    # Prepara il contesto
    context = {
        'project': project,
        'tasks': tasks,
    }
    
    return render(request, 'projects/project_gantt.html', context)

def generate_municipality_report(request, pk):
    from io import BytesIO
    municipality = get_object_or_404(Municipality, pk=pk)
    
    # Genera il PDF
    buffer = BytesIO()
    report_generator = MunicipalityReportGenerator(municipality, buffer)
    pdf = report_generator.generate()
    
    # Crea la risposta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{municipality.name}_report.pdf"'
    response.write(pdf.getvalue())
    
    return response

def generate_project_report(request, pk):
    project = get_object_or_404(ChargingProject, pk=pk)
    
    # Genera il PDF
    buffer = BytesIO()
    report_generator = ChargingProjectReportGenerator(project, buffer)
    pdf = report_generator.generate()
    
    # Crea la risposta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{project.name}_business_plan.pdf"'
    response.write(pdf.getvalue())
    
    return response

def generate_station_sheet(request, pk):
    station = get_object_or_404(ChargingStation, pk=pk)
    
    # Genera il PDF
    buffer = BytesIO()
    sheet_generator = ChargingStationSheetGenerator(station, buffer)
    pdf = sheet_generator.generate()
    
    # Crea la risposta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{station.code}_scheda_tecnica.pdf"'
    response.write(pdf.getvalue())
    
    return response

# Viste per le impostazioni globali
class GlobalSettingsView(LoginRequiredMixin, CreateView):
    model = GlobalSettings
    form_class = GlobalSettingsForm
    template_name = 'infrastructure/global_settings_form.html'
    success_url = reverse_lazy('infrastructure:tech-config')
    
    def get_initial(self):
        """Controlla se esiste già una configurazione attiva e la utilizza come base"""
        initial = super().get_initial()
        try:
            active_settings = GlobalSettings.get_active()
            # Pre-compila il form con i valori esistenti
            for field in self.form_class.Meta.fields:
                if hasattr(active_settings, field):
                    initial[field] = getattr(active_settings, field)
        except Exception:
            # Usa i valori predefiniti se non c'è una configurazione attiva
            pass
        return initial
    
    def form_valid(self, form):
        messages.success(self.request, _("Impostazioni globali salvate con successo!"))
        return super().form_valid(form)

class GlobalSettingsUpdateView(LoginRequiredMixin, UpdateView):
    model = GlobalSettings
    form_class = GlobalSettingsForm
    template_name = 'infrastructure/global_settings_form.html'
    success_url = reverse_lazy('infrastructure:tech-config')
    
    def form_valid(self, form):
        messages.success(self.request, _("Impostazioni globali aggiornate con successo!"))
        return super().form_valid(form)

def dashboard(request):
    """Dashboard principale dell'infrastruttura"""
    import json
    from datetime import datetime, timedelta
    import random
    from cpo_core.models import Project, SubProject
    from cpo_core.models.subproject import Charger
    from decimal import Decimal
    
    # Definiamo un encoder JSON personalizzato per gestire i Decimal
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                return float(obj)
            return super(DecimalEncoder, self).default(obj)
    
    # Conta i progetti e le stazioni
    projects_count = Project.objects.count()
    stations_count = SubProject.objects.count()
    chargers_count = Charger.objects.count()
    municipalities_with_projects = Municipality.objects.filter(
        id__in=SubProject.objects.values_list('municipality_id', flat=True).distinct()
    ).count()
    
    # Seleziona il numero più alto tra stazioni e colonnine 
    display_stations_count = max(stations_count, chargers_count)
    
    # Statistiche di base
    active_projects = Project.objects.filter(status='in_progress').count()
    
    # Calcola potenza totale installata
    total_power = 0
    # Somma la potenza di tutte le colonnine
    for charger in Charger.objects.all():
        if charger.power_kw:
            total_power += float(charger.power_kw)
    # Se non ci sono colonnine, usa la potenza dei sottoprogetti
    if total_power == 0:
        for sp in SubProject.objects.all():
            if sp.power_kw:
                total_power += float(sp.power_kw)
    
    # Progetti per stato
    planning_projects = Project.objects.filter(status='planning').count()
    in_progress_projects = Project.objects.filter(status='in_progress').count()
    completed_projects = Project.objects.filter(status='completed').count()
    paused_projects = Project.objects.filter(status='suspended').count() 
    cancelled_projects = Project.objects.filter(status='closed').count()
    
    # Stazioni per stato
    planned_stations = Charger.objects.filter(status='planned').count()
    installing_stations = Charger.objects.filter(status='installing').count()
    active_stations = Charger.objects.filter(status='operational').count()
    maintenance_stations = Charger.objects.filter(status='maintenance').count()
    inactive_stations = Charger.objects.filter(status='offline').count()
    
    # Se non ci sono colonnine, imposta almeno alcuni valori di esempio
    if planned_stations + installing_stations + active_stations + maintenance_stations + inactive_stations == 0:
        planned_stations = 1
        active_stations = 2
    
    # Dati finanziari di esempio per grafici
    total_investment = 150000  # Valore di esempio fisso
    total_revenue = 180000     # Valore di esempio fisso
    average_roi = 15.0         # Percentuale ROI media (esempio)
    investment_return_time = 5.5  # Anni per recuperare l'investimento (esempio)
    
    # Dati stazioni con coordinate
    stations_with_coords = []
    # Aggiungi un marker per ogni sottoprogetto che ha coordinate
    for sp in SubProject.objects.filter(
        latitude_approved__isnull=False, 
        longitude_approved__isnull=False
    ).prefetch_related('project', 'project__organization'):
        stations_with_coords.append({
            'id': sp.id,
            'code': sp.name,
            'name': sp.name,
            'project': {'name': sp.project.name} if sp.project else {'name': 'Progetto sconosciuto'},
            'latitude': sp.latitude_approved,
            'longitude': sp.longitude_approved,
            'power_kw': sp.power_kw or 50,
            'location': sp.address or 'Indirizzo non disponibile',
            'status': 'active'  # Default status for display
        })
    
    # Cerca di ottenere comuni specifici per mostrare punti sulla mappa
    try:
        # Cerca comuni con progetti
        municipalities_with_subprojects = Municipality.objects.filter(
            id__in=SubProject.objects.values_list('municipality_id', flat=True)
        )
        
        # Se ci sono comuni con progetti, visualizzali sulla mappa
        if municipalities_with_subprojects.exists():
            for mun in municipalities_with_subprojects[:5]:  # Limitiamo a 5 per non sovraccaricare
                # Ottieni i sottoprogetti di questo comune
                mun_subprojects = SubProject.objects.filter(municipality=mun)
                
                for sp in mun_subprojects:
                    # Usa le coordinate proposte se quelle approvate non ci sono
                    lat = sp.latitude_approved if sp.latitude_approved else (sp.latitude_proposed if sp.latitude_proposed else None)
                    lng = sp.longitude_approved if sp.longitude_approved else (sp.longitude_proposed if sp.longitude_proposed else None)
                    
                    if lat and lng:
                        stations_with_coords.append({
                            'id': sp.id,
                            'code': sp.name,
                            'name': sp.name,
                            'project': {'name': sp.project.name} if sp.project else {'name': f'Progetto {mun.name}'},
                            'latitude': lat,
                            'longitude': lng,
                            'power_kw': sp.power_kw or 50,
                            'location': sp.address or f'Indirizzo in {mun.name}',
                            'status': 'active'
                        })
        
        # Se non ci sono punti, aggiungi un punto di esempio (solo se non ci sono altri punti)
        if not stations_with_coords:
            # Ottieni un comune qualsiasi per un punto di esempio
            sample_municipality = Municipality.objects.order_by('?').first()
            if sample_municipality:
                stations_with_coords.append({
                    'id': 1,
                    'code': f'{sample_municipality.name[:3].upper()}-001',
                    'name': f'Stazione {sample_municipality.name}',
                    'project': {'name': f'Progetto {sample_municipality.name}'},
                    'latitude': 45.0,  # Coordinate di esempio (centrate in Italia)
                    'longitude': 12.0,
                    'power_kw': 50,
                    'location': f'Centro di {sample_municipality.name}',
                    'status': 'active'
                })
    except Exception as e:
        # In caso di errore, non blocchiamo il rendering della dashboard
        print(f"Errore nel caricamento delle stazioni per la mappa: {e}")
    
    # Dati crescita mensile (ultimi 12 mesi)
    today = datetime.now()
    months = []
    growth_stations = []
    growth_power = []
    
    for i in range(12):
        month_date = today - timedelta(days=30 * (11-i))
        month_name = month_date.strftime("%b %Y")
        months.append(month_name)
        # Crea una crescita più realistica
        growth_stations.append(max(1, i))  # Da 0 a 11 stazioni
        growth_power.append(max(1, i) * 50)  # Da 0 a 550 kW
    
    # Dati finanziari annuali
    current_year = today.year
    financial_years = [str(current_year-2), str(current_year-1), str(current_year), 
                      str(current_year+1), str(current_year+2)]
    # Usa valori fissi più realistici
    financial_investments = [50000, 70000, 100000, 60000, 40000]
    financial_revenues = [10000, 40000, 90000, 120000, 150000]
    
    # Distribuzione della potenza
    power_distribution = [1, 1, 1, 0, 0]  # Default values
    
    # Progetti recenti - prendi solo quelli del modello cpo_core
    recent_projects = Project.objects.all().order_by('-id')[:5]
    
    # Per ciascun progetto recente, assicurati che abbia attributi necessari per il template
    for project in recent_projects:
        if not hasattr(project, 'municipality'):
            # Se il progetto non ha un comune associato, imposta region come attributo
            project.region = 'Veneto'
        if not hasattr(project, 'completion_percentage'):
            # Aggiungi un metodo per il calcolo della percentuale di completamento
            project.completion_percentage = 50
        if not hasattr(project, 'get_status_color'):
            # Aggiungi un metodo per determinare il colore dello stato
            project.get_status_color = lambda: 'primary'
    
    # Calcola percentuali di crescita per le statistiche
    new_projects_percent = 15  # Valore esempio
    new_stations_percent = 20  # Valore esempio
    new_power_percent = 25     # Valore esempio
    new_municipalities_percent = 10  # Valore esempio
    
    # Add empty upcoming_tasks variable for the template
    upcoming_tasks = []
    
    context = {
        # KPI principali
        'total_projects': projects_count,
        'total_stations': display_stations_count,
        'total_municipalities': municipalities_with_projects,
        'total_power': int(total_power),
        
        # Percentuali di crescita
        'new_projects_percent': new_projects_percent,
        'new_stations_percent': new_stations_percent,
        'new_power_percent': new_power_percent,
        'new_municipalities_percent': new_municipalities_percent,
        
        # Dati progetti per stato
        'planning_projects': planning_projects,
        'in_progress_projects': in_progress_projects,
        'completed_projects': completed_projects,
        'paused_projects': paused_projects,
        'cancelled_projects': cancelled_projects,
        
        # Dati stazioni per stato
        'planned_stations': planned_stations,
        'installing_stations': installing_stations,
        'active_stations': active_stations,
        'maintenance_stations': maintenance_stations,
        'inactive_stations': inactive_stations,
        
        # Dati finanziari
        'total_investment': total_investment,
        'total_revenue': total_revenue,
        'average_roi': average_roi,
        'investment_return_time': investment_return_time,
        
        # Dati per grafici
        'station_types': {'ac': 2, 'dc': 1},  # Esempio di tipi di stazioni
        'stations_with_coords': json.dumps(stations_with_coords, cls=DecimalEncoder),  # Passa come JSON per debugging
        'stations_with_coords_raw': stations_with_coords,  # Passa anche i dati raw per il rendering dei marker
        'growth_months': json.dumps(months, cls=DecimalEncoder),
        'growth_stations': json.dumps(growth_stations, cls=DecimalEncoder),
        'growth_power': json.dumps(growth_power, cls=DecimalEncoder),
        'financial_years': json.dumps(financial_years, cls=DecimalEncoder),
        'financial_investments': json.dumps(financial_investments, cls=DecimalEncoder),
        'financial_revenues': json.dumps(financial_revenues, cls=DecimalEncoder),
        'power_distribution': json.dumps(power_distribution, cls=DecimalEncoder),
        
        # Dati progetti recenti
        'recent_projects': recent_projects,
        
        # Prossime attività
        'upcoming_tasks': upcoming_tasks,
    }
    
    return render(request, 'infrastructure/dashboard.html', context)

def tech_config_dashboard(request):
    # Recupera le configurazioni attive
    active_electricity_tariffs = ElectricityTariff.objects.filter(active=True)
    active_management_fees = ManagementFee.objects.filter(active=True)
    
    # Recupera le impostazioni globali
    try:
        global_settings = GlobalSettings.get_active()
    except:
        global_settings = None
    
    # Conta tutti i profili e template
    usage_profiles_count = StationUsageProfile.objects.count()
    station_templates_count = ChargingStationTemplate.objects.count()
    
    # Statistiche stazioni per tipologia
    station_types = ChargingStation.objects.values('connection_type').annotate(
        count=Count('id'),
        avg_power=Avg('max_power'),
        total_power=Sum('max_power')
    )
    
    # Stima economica totale basata sui profili
    total_monthly_revenue = 0
    if active_management_fees.exists() and StationUsageProfile.objects.exists():
        default_profile = StationUsageProfile.objects.first()
        default_fee = active_management_fees.first()
        
        for station in ChargingStation.objects.filter(status='active'):
            monthly_kwh = default_profile.calculate_monthly_usage(station.max_power)
            # Applica il prezzo cliente in base alla potenza
            if station.max_power <= 7:
                price = float(default_fee.customer_price_tier1)
            elif station.max_power <= 22:
                price = float(default_fee.customer_price_tier2)
            elif station.max_power <= 50:
                price = float(default_fee.customer_price_tier3)
            elif station.max_power <= 150:
                price = float(default_fee.customer_price_tier4)
            else:
                price = float(default_fee.customer_price_tier5)
                
            station_revenue = monthly_kwh * price
            total_monthly_revenue += station_revenue
    
    context = {
        'active_electricity_tariffs': active_electricity_tariffs,
        'active_management_fees': active_management_fees,
        'usage_profiles_count': usage_profiles_count,
        'station_templates_count': station_templates_count,
        'station_types': station_types,
        'total_monthly_revenue': total_monthly_revenue,
        'total_annual_revenue': total_monthly_revenue * 12
    }
    
    return render(request, 'infrastructure/tech_config_dashboard.html', context)

# Views for ElectricityTariff
class ElectricityTariffListView(LoginRequiredMixin, ListView):
    model = ElectricityTariff
    context_object_name = 'tariffs'
    template_name = 'infrastructure/tariff_list.html'
    
class ElectricityTariffDetailView(LoginRequiredMixin, DetailView):
    model = ElectricityTariff
    context_object_name = 'tariff'
    template_name = 'infrastructure/tariff_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calcola i costi medi per diverse potenze di stazione
        context['cost_examples'] = [
            {'power': '7 kW AC', 'cost': self.object.cost_tier1, 'monthly': 7 * 5 * 30 * float(self.object.cost_tier1)},
            {'power': '22 kW AC', 'cost': self.object.cost_tier2, 'monthly': 22 * 5 * 30 * float(self.object.cost_tier2)},
            {'power': '50 kW DC', 'cost': self.object.cost_tier3, 'monthly': 50 * 3 * 30 * float(self.object.cost_tier3)},
            {'power': '150 kW DC', 'cost': self.object.cost_tier4, 'monthly': 150 * 2 * 30 * float(self.object.cost_tier4)},
            {'power': '350 kW DC', 'cost': self.object.cost_tier5, 'monthly': 350 * 1 * 30 * float(self.object.cost_tier5)},
        ]
        return context
    
class ElectricityTariffCreateView(LoginRequiredMixin, CreateView):
    model = ElectricityTariff
    form_class = ElectricityTariffForm
    template_name = 'infrastructure/tariff_form.html'
    success_url = reverse_lazy('infrastructure:tariff-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Tariffa elettrica '{form.instance.name}' creata con successo!")
        return super().form_valid(form)

class PunTariffCreateView(LoginRequiredMixin, CreateView):
    model = ElectricityTariff
    form_class = ElectricityTariffForm
    template_name = 'infrastructure/pun_tariff_form.html'
    success_url = reverse_lazy('infrastructure:tariff-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date
        context['today'] = date.today()
        return context
    
    def form_valid(self, form):
        form.instance.tariff_type = 'pun'  # Forza il tipo tariffa a PUN
        messages.success(self.request, f"Tariffa PUN '{form.instance.name}' creata con successo!")
        return super().form_valid(form)

class ElectricityTariffUpdateView(LoginRequiredMixin, UpdateView):
    model = ElectricityTariff
    form_class = ElectricityTariffForm
    template_name = 'infrastructure/tariff_form.html'
    success_url = reverse_lazy('infrastructure:tariff-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Tariffa elettrica '{form.instance.name}' aggiornata con successo!")
        return super().form_valid(form)


# Viste per i dati PUN
class PunDataListView(LoginRequiredMixin, ListView):
    model = PunData
    context_object_name = 'pun_data'
    template_name = 'infrastructure/pun_data_list.html'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtra per data
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
            
        # Filtra per fascia
        timeband = self.request.GET.get('timeband')
        if timeband:
            queryset = queryset.filter(timeband=timeband)
            
        # Filtra per zona
        zone = self.request.GET.get('zone')
        if zone:
            queryset = queryset.filter(zone=zone)
            
        return queryset.order_by('-date', 'hour')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calcola prezzo medio per fascia
        f1_avg = PunData.objects.filter(timeband='F1').aggregate(avg=models.Avg('price'))['avg'] or 0
        f2_avg = PunData.objects.filter(timeband='F2').aggregate(avg=models.Avg('price'))['avg'] or 0
        f3_avg = PunData.objects.filter(timeband='F3').aggregate(avg=models.Avg('price'))['avg'] or 0
        
        # Converti da €/MWh a €/kWh per visualizzazione
        context['f1_avg_kwh'] = f1_avg / 1000
        context['f2_avg_kwh'] = f2_avg / 1000
        context['f3_avg_kwh'] = f3_avg / 1000
        
        # Conta dati per zona
        context['data_by_zone'] = PunData.objects.values('zone').annotate(count=models.Count('id'))
        
        # Aggiungi filtri correnti al contesto
        context['current_filters'] = {
            'date_from': self.request.GET.get('date_from', ''),
            'date_to': self.request.GET.get('date_to', ''),
            'timeband': self.request.GET.get('timeband', ''),
            'zone': self.request.GET.get('zone', ''),
        }
        
        return context

class PunDataDownloadView(LoginRequiredMixin, FormView):
    template_name = 'infrastructure/pun_data_download.html'
    form_class = EnergyPriceProjectionForm
    success_url = reverse_lazy('infrastructure:pun-data-list')
    
    def form_valid(self, form):
        include_download = form.cleaned_data.get('include_download')
        start_date = form.cleaned_data.get('start_date')
        months_ahead = form.cleaned_data.get('months_ahead', 12)
        
        if include_download:
            # Scarica dati PUN
            success = PunDataService.download_pun_data(
                start_date=start_date, 
                end_date=datetime.now().date()
            )
            
            if success:
                messages.success(self.request, _("Dati PUN scaricati con successo!"))
            else:
                messages.error(self.request, _("Errore durante lo scaricamento dei dati PUN."))
        
        # Genera proiezioni
        success = PunDataService.generate_projections(months_ahead=months_ahead)
        
        if success:
            messages.success(self.request, _(f"Proiezioni generate per {months_ahead} mesi con successo!"))
        else:
            messages.error(self.request, _("Errore durante la generazione delle proiezioni."))
            
        return super().form_valid(form)

class EnergyPriceProjectionListView(LoginRequiredMixin, ListView):
    model = EnergyPriceProjection
    context_object_name = 'projections'
    template_name = 'infrastructure/energy_projection_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Ottieni inflazione dalle impostazioni
        settings = GlobalSettings.get_active()
        context['inflation_rate'] = settings.inflation_rate
        
        # Calcola prezzo medio attuale del PUN
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        try:
            current_projection = EnergyPriceProjection.objects.get(
                year=current_year,
                month=current_month
            )
            context['current_projection'] = current_projection
        except EnergyPriceProjection.DoesNotExist:
            context['current_projection'] = None
        
        return context

# Views for ManagementFee
class ManagementFeeListView(LoginRequiredMixin, ListView):
    model = ManagementFee
    context_object_name = 'fees'
    template_name = 'infrastructure/fee_list.html'

class ManagementFeeDetailView(LoginRequiredMixin, DetailView):
    model = ManagementFee
    context_object_name = 'fee'
    template_name = 'infrastructure/fee_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Se esiste una tariffa elettrica attiva, calcola il margine
        active_tariff = ElectricityTariff.objects.filter(active=True).first()
        if active_tariff:
            # Calcola i margini per diverse potenze
            context['margin_examples'] = [
                {'power': '7 kW AC', **self.object.calculate_margin(active_tariff, 7)},
                {'power': '22 kW AC', **self.object.calculate_margin(active_tariff, 22)},
                {'power': '50 kW DC', **self.object.calculate_margin(active_tariff, 50)},
                {'power': '150 kW DC', **self.object.calculate_margin(active_tariff, 150)},
                {'power': '350 kW DC', **self.object.calculate_margin(active_tariff, 350)},
            ]
            context['active_tariff'] = active_tariff
        
        return context

class ManagementFeeCreateView(LoginRequiredMixin, CreateView):
    model = ManagementFee
    form_class = ManagementFeeForm
    template_name = 'infrastructure/fee_form.html'
    success_url = reverse_lazy('infrastructure:fee-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Configurazione tariffaria '{form.instance.name}' creata con successo!")
        return super().form_valid(form)

class ManagementFeeUpdateView(LoginRequiredMixin, UpdateView):
    model = ManagementFee
    form_class = ManagementFeeForm
    template_name = 'infrastructure/fee_form.html'
    success_url = reverse_lazy('infrastructure:fee-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Configurazione tariffaria '{form.instance.name}' aggiornata con successo!")
        return super().form_valid(form)

# Views for StationUsageProfile
class StationUsageProfileListView(LoginRequiredMixin, ListView):
    model = StationUsageProfile
    context_object_name = 'profiles'
    template_name = 'infrastructure/profile_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Profili di utilizzo stazioni'
        return context

class StationUsageProfileDetailView(LoginRequiredMixin, DetailView):
    model = StationUsageProfile
    context_object_name = 'profile'
    template_name = 'infrastructure/profile_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"{self.object.name} - Profilo di utilizzo stazione"
        # Calcola esempio utilizzo per diverse potenze
        context['usage_examples'] = [
            {'power': '7 kW AC', 'monthly_usage': self.object.calculate_monthly_usage(7)},
            {'power': '22 kW AC', 'monthly_usage': self.object.calculate_monthly_usage(22)},
            {'power': '50 kW DC', 'monthly_usage': self.object.calculate_monthly_usage(50)},
            {'power': '150 kW DC', 'monthly_usage': self.object.calculate_monthly_usage(150)},
            {'power': '350 kW DC', 'monthly_usage': self.object.calculate_monthly_usage(350)},
        ]
        return context

class StationUsageProfileCreateView(LoginRequiredMixin, CreateView):
    model = StationUsageProfile
    form_class = StationUsageProfileForm
    template_name = 'infrastructure/profile_form.html'
    success_url = reverse_lazy('infrastructure:profile-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Nuovo profilo di utilizzo'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f"Profilo di utilizzo '{form.instance.name}' creato con successo!")
        return super().form_valid(form)

class StationUsageProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = StationUsageProfile
    form_class = StationUsageProfileForm
    template_name = 'infrastructure/profile_form.html'
    success_url = reverse_lazy('infrastructure:profile-list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = f"Modifica profilo: {self.object.name}"
        return context
    
    def form_valid(self, form):
        messages.success(self.request, f"Profilo di utilizzo '{form.instance.name}' aggiornato con successo!")
        return super().form_valid(form)

# Views for ChargingStationTemplate
class ChargingStationTemplateListView(LoginRequiredMixin, ListView):
    model = ChargingStationTemplate
    context_object_name = 'templates'
    template_name = 'infrastructure/station_template_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Raggruppa i template per marca
        context['templates_by_brand'] = {}
        for template in context['templates']:
            if template.brand not in context['templates_by_brand']:
                context['templates_by_brand'][template.brand] = []
            context['templates_by_brand'][template.brand].append(template)
        return context

class ChargingStationTemplateDetailView(LoginRequiredMixin, DetailView):
    model = ChargingStationTemplate
    context_object_name = 'template'
    template_name = 'infrastructure/station_template_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calcola costo totale
        context['total_cost'] = self.object.calculate_total_cost()
        context['annual_cost'] = self.object.calculate_annual_cost()
        
        # Se esiste una tariffa elettrica e un profilo di utilizzo, calcola costi operativi
        active_tariff = ElectricityTariff.objects.filter(active=True).first()
        default_profile = StationUsageProfile.objects.first()
        if active_tariff and default_profile:
            monthly_kwh = default_profile.calculate_monthly_usage(self.object.power_kw)
            
            # Determina il costo in base alla potenza
            if self.object.power_kw <= 7:
                kwh_cost = float(active_tariff.cost_tier1)
            elif self.object.power_kw <= 22:
                kwh_cost = float(active_tariff.cost_tier2)
            elif self.object.power_kw <= 50:
                kwh_cost = float(active_tariff.cost_tier3)
            elif self.object.power_kw <= 150:
                kwh_cost = float(active_tariff.cost_tier4)
            else:
                kwh_cost = float(active_tariff.cost_tier5)
                
            monthly_energy_cost = monthly_kwh * kwh_cost
            monthly_fixed_cost = float(active_tariff.connection_fee) + (self.object.power_kw * float(active_tariff.power_fee))
            
            context['monthly_energy_cost'] = monthly_energy_cost
            context['monthly_fixed_cost'] = monthly_fixed_cost
            context['monthly_total_cost'] = monthly_energy_cost + monthly_fixed_cost
            context['annual_operating_cost'] = (monthly_energy_cost + monthly_fixed_cost) * 12
            context['active_tariff'] = active_tariff
            context['usage_profile'] = default_profile
            
        return context

class ChargingStationTemplateCreateView(LoginRequiredMixin, CreateView):
    model = ChargingStationTemplate
    form_class = ChargingStationTemplateForm
    template_name = 'infrastructure/station_template_form.html'
    success_url = reverse_lazy('infrastructure:template-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Template '{form.instance.name}' creato con successo!")
        return super().form_valid(form)

class ChargingStationTemplateUpdateView(LoginRequiredMixin, UpdateView):
    model = ChargingStationTemplate
    form_class = ChargingStationTemplateForm
    template_name = 'infrastructure/station_template_form.html'
    success_url = reverse_lazy('infrastructure:template-list')
    
    def form_valid(self, form):
        messages.success(self.request, f"Template '{form.instance.name}' aggiornato con successo!")
        return super().form_valid(form)
        
# Station Quick Create from Template
def station_from_template(request, template_id, project_id=None):
    template = get_object_or_404(ChargingStationTemplate, pk=template_id)
    
    if request.method == 'POST':
        form = ChargingStationForm(request.POST)
        if form.is_valid():
            station = form.save(commit=False)
            # Utilizza i dati dal template se non specificati
            if project_id and not station.project_id:
                station.project_id = project_id
            station.save()
            messages.success(request, f"Stazione di ricarica '{station.code}' creata dal template '{template.name}'!")
            
            if project_id:
                return redirect('infrastructure:project-detail', pk=project_id)
            else:
                return redirect('infrastructure:station-detail', pk=station.pk)
    else:
        # Preleva i dati dal template
        initial_data = {
            'connection_type': template.connection_type,
            'max_power': template.power_kw,
            'num_connectors': template.num_connectors,
            'purchase_cost': template.purchase_cost,
            'installation_cost': template.installation_cost,
            'ground_area': template.ground_area,
            'modem_4g_cost': template.modem_4g_cost,
            'sim_annual_cost': template.sim_annual_cost,
            'has_4g': template.has_4g,
        }
        
        if project_id:
            initial_data['project'] = project_id
            
        form = ChargingStationForm(initial=initial_data)
    
    context = {
        'form': form,
        'template': template,
        'project_id': project_id
    }
    
    return render(request, 'infrastructure/station_from_template.html', context)