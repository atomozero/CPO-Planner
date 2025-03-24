# cpo_planner/projects/views/subproject_views.py
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _

# Importa dai modelli consolidati
from cpo_core.models.project import Project
from cpo_core.models.subproject import SubProject
from cpo_core.models.municipality import Municipality
from ..forms.subproject_forms import SubProjectForm

class SubProjectDetailView(LoginRequiredMixin, DetailView):
    model = SubProject
    template_name = 'projects/subproject_detail.html'
    context_object_name = 'subproject'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        
        # Calcola i giorni di indisponibilità e il fattore di disponibilità
        unavailable_days = 0
        if self.object.weekly_market_day is not None:
            unavailable_days += 52  # 52 settimane all'anno
        
        # Aggiungi giorni di festa locale
        if self.object.local_festival_days:
            unavailable_days += self.object.local_festival_days
            
        # Calcola il fattore di disponibilità
        total_days = 365
        available_days = total_days - unavailable_days
        availability_factor = available_days / total_days if total_days > 0 else 1.0
        
        # Aggiungi al contesto
        context['unavailable_days'] = unavailable_days
        context['available_days'] = available_days
        context['availability_factor'] = availability_factor
        
        # Ottieni le foto della stazione
        from cpo_core.models.charging_station import ChargingStationPhoto
        from cpo_core.models.charging_station import ChargingStation
        
        # Cerca una stazione di ricarica associata a questo subproject
        charging_station = None
        try:
            # Prova a cercare una stazione di ricarica con lo stesso ID
            charging_station = ChargingStation.objects.filter(subproject_id=self.object.id).first()
        except:
            pass
        
        # Cerca foto associate al subproject o alla stazione di ricarica
        # Creiamo una query combinata per entrambe le relazioni
        photos_from_subproject = ChargingStationPhoto.objects.filter(subproject=self.object)
        
        if charging_station:
            # Se abbiamo trovato una stazione di ricarica, aggiungi anche le sue foto
            photos_from_charging_station = ChargingStationPhoto.objects.filter(charging_station=charging_station)
            # Combina i due queryset
            station_photos = photos_from_subproject.union(photos_from_charging_station).order_by('-date_taken', '-created_at')
        else:
            # Altrimenti, usa solo le foto legate direttamente al subproject
            station_photos = photos_from_subproject.order_by('-date_taken', '-created_at')
            
        # Debug: stampa il numero di foto trovate
        print(f"DEBUG: Trovate {station_photos.count()} foto per il subproject {self.object.id}")
        
        context['station_photos'] = station_photos
        context['pre_installation_photos'] = ChargingStationPhoto.objects.filter(
            subproject=self.object, phase='pre_installation').order_by('-date_taken', '-created_at')
        context['during_installation_photos'] = ChargingStationPhoto.objects.filter(
            subproject=self.object, phase='during_installation').order_by('-date_taken', '-created_at')
        context['post_installation_photos'] = ChargingStationPhoto.objects.filter(
            subproject=self.object, phase='post_installation').order_by('-date_taken', '-created_at')
        
        return context

class SubProjectCreateView(LoginRequiredMixin, CreateView):
    model = SubProject
    form_class = SubProjectForm
    template_name = 'projects/subproject_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_id'] = self.kwargs.get('project_id')
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project_id = self.kwargs.get('project_id')
        context['project'] = get_object_or_404(Project, pk=project_id)
        context['title'] = _('Crea Nuova Stazione di Ricarica')
        
        # Aggiungi i template di stazioni disponibili
        from infrastructure.models import ChargingStationTemplate
        templates = ChargingStationTemplate.objects.all().order_by('brand', 'model')
        # Stampa debug dei template per aiutare la risoluzione dei problemi
        debug_info = []
        for template in templates:
            debug_info.append({
                'id': template.id,
                'brand': template.brand,
                'model': template.model,
                'power_kw': template.power_kw,
                'ground_area': template.ground_area
            })
        print("DEBUG - Templates disponibili:", debug_info)
        context['charging_templates'] = templates
        return context
    
    def form_valid(self, form):
        # Imposta il progetto
        form.instance.project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, pk=self.kwargs.get('project_id'))
        
        # Imposta il comune del sottoprogetto uguale a quello specificato nel progetto
        municipality = None
        
        # Prova a trovare il comune basandosi sulla regione del progetto
        if project.region:
            municipality = Municipality.objects.filter(name=project.region).first()
        
        # Se non è stato trovato un comune basandosi sulla regione, cerca un comune associato al progetto
        if not municipality and hasattr(project, 'municipality') and project.municipality:
            municipality = project.municipality
        
        # Se ancora non abbiamo un comune, cerca di creare un comune generico
        if not municipality:
            # Opzione 1: usa il primo comune disponibile nel database
            municipality = Municipality.objects.first()
            
            # Opzione 2: crea un nuovo comune con il nome della regione o un nome generico
            if not municipality:
                name = project.region or "Comune Generico"
                municipality = Municipality.objects.create(
                    name=name,
                    province="Provincia Generica",
                    region="Regione Generica"
                )
        
        # Assegna il comune trovato o creato
        if municipality:
            form.instance.municipality = municipality
        else:
            # Se proprio non c'è modo di trovare o creare un comune, segnala l'errore
            messages.error(self.request, "Impossibile trovare o creare un comune. Verificare le impostazioni del progetto.")
            return self.form_invalid(form)
        
        messages.success(self.request, _('Stazione di ricarica creata con successo!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.kwargs.get('project_id')})

class SubProjectUpdateView(LoginRequiredMixin, UpdateView):
    model = SubProject
    form_class = SubProjectForm
    template_name = 'projects/subproject_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project_id'] = self.object.project_id
        
        # Debug dei dati che arrivano al form
        print("DEBUG - get_form_kwargs SubProjectUpdateView - instance:", self.object)
        print("DEBUG - get_form_kwargs SubProjectUpdateView - instance values:", {
            'power_kw': self.object.power_kw,
            'ground_area_sqm': self.object.ground_area_sqm,
            'equipment_cost': self.object.equipment_cost,
            'installation_cost': self.object.installation_cost,
            'connection_cost': self.object.connection_cost
        })
        
        return kwargs
        
    def form_valid(self, form):
        # Ottieni il progetto associato al sottoprogetto
        project = self.object.project
        
        # Imposta il comune del sottoprogetto uguale a quello specificato nel progetto
        if project.region:
            municipality = Municipality.objects.filter(name=project.region).first()
            if municipality:
                form.instance.municipality = municipality
        
        # Debug: mostra i valori dei campi economici prima del salvataggio
        print("DEBUG - SubProjectUpdateView form_valid - Valori del form:", {
            'equipment_cost': form.cleaned_data.get('equipment_cost'),
            'installation_cost': form.cleaned_data.get('installation_cost'),
            'connection_cost': form.cleaned_data.get('connection_cost'),
            'permit_cost': form.cleaned_data.get('permit_cost'),
            'civil_works_cost': form.cleaned_data.get('civil_works_cost'),
            'other_costs': form.cleaned_data.get('other_costs'),
            'budget': form.cleaned_data.get('budget')
        })
        
        # Assicura che il modello utilizzi i valori esatti del form per i campi economici
        form.instance.equipment_cost = form.cleaned_data.get('equipment_cost')
        form.instance.installation_cost = form.cleaned_data.get('installation_cost')
        form.instance.connection_cost = form.cleaned_data.get('connection_cost')
        form.instance.permit_cost = form.cleaned_data.get('permit_cost')
        form.instance.civil_works_cost = form.cleaned_data.get('civil_works_cost')
        form.instance.other_costs = form.cleaned_data.get('other_costs')
        
        # Se il budget è stato calcolato manualmente nel form, usalo
        if form.cleaned_data.get('budget'):
            form.instance.budget = form.cleaned_data.get('budget')
            print(f"DEBUG - Usando budget dal form: {form.cleaned_data.get('budget')}")
        
        messages.success(self.request, _('Stazione di ricarica aggiornata con successo!'))
        return super().form_valid(form)
    
    def post(self, request, *args, **kwargs):
        # Gestisci richieste AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and 'status' in request.POST:
            # Ottieni l'oggetto da aggiornare
            self.object = self.get_object()
            
            # Crea un form con solo il campo status
            from django.forms import modelform_factory
            ModelForm = modelform_factory(self.model, fields=['status'])
            form = ModelForm(request.POST, instance=self.object)
            
            if form.is_valid():
                # Imposta i campi di tracciamento
                from django.utils import timezone
                self.object.status_changed_date = timezone.now()
                self.object.status_changed_by = request.user if request.user.is_authenticated else None
                
                # Imposta lo stato e salva
                self.object.status = form.cleaned_data['status']
                self.object.save()
                
                # Restituisci una risposta JSON
                from django.http import JsonResponse
                return JsonResponse({
                    'success': True,
                    'status': self.object.get_status_display()
                })
            else:
                from django.http import JsonResponse
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
                
        return super().post(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.object.project
        context['title'] = _('Modifica Sotto-Progetto')
        
        # Debug: stampa i valori del form per identificare problemi
        debug_info = {
            'power_kw': self.object.power_kw,
            'ground_area_sqm': self.object.ground_area_sqm,
            'equipment_cost': self.object.equipment_cost,
            'installation_cost': self.object.installation_cost,
            'connection_cost': self.object.connection_cost,
            'permit_cost': self.object.permit_cost,
            'civil_works_cost': getattr(self.object, 'civil_works_cost', None),
            'other_costs': self.object.other_costs,
        }
        print("DEBUG - Valori del subproject:", debug_info)
        
        # Aggiungi i template di stazioni disponibili
        from infrastructure.models import ChargingStationTemplate
        templates = ChargingStationTemplate.objects.all().order_by('brand', 'model')
        context['charging_templates'] = templates
        
        # Se siamo in modalità aggiornamento rapido dello stato
        if 'status' in self.request.GET or (hasattr(self, 'fields') and self.fields == ['status']):
            context['status_only'] = True
            context['status_choices'] = SubProject.STATUS_CHOICES
            context['title'] = _('Aggiorna Stato')
            
        return context
    
    def get_form_class(self):
        # Gestisci richieste AJAX per aggiornamento dello stato
        is_ajax_status_update = (
            self.request.method == 'POST' and
            self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' and
            'status' in self.request.POST and 
            len(self.request.POST) == 1
        )
        
        # Se viene specificato fields direttamente nella URL conf, usa un ModelForm di base
        if hasattr(self, 'fields') and self.fields:
            from django.forms import modelform_factory
            return modelform_factory(self.model, fields=self.fields)
        # Se la richiesta è un aggiornamento di stato via AJAX
        elif is_ajax_status_update:
            from django.forms import modelform_factory
            return modelform_factory(self.model, fields=['status'])
        # Se il parametro status è presente nella richiesta POST normale, crea un form solo per lo stato
        elif self.request.method == 'POST' and 'status' in self.request.POST and len(self.request.POST) <= 2:
            # 2 perché abbiamo csrfmiddlewaretoken e status
            from django.forms import modelform_factory
            return modelform_factory(self.model, fields=['status'])
        # Altrimenti usa il form completo
        return self.form_class
    
    def form_valid(self, form):
        # Se la richiesta è AJAX e contiene solo lo status
        is_ajax_status_update = self.request.headers.get('X-Requested-With') == 'XMLHttpRequest' and len(self.request.POST) == 1 and 'status' in self.request.POST
        
        # Se stiamo aggiornando lo stato (o tramite form o tramite AJAX)
        if 'status' in form.changed_data or is_ajax_status_update:
            from django.utils import timezone
            # Imposta la data di modifica dello stato
            form.instance.status_changed_date = timezone.now()
            # Imposta l'utente che ha modificato lo stato
            if self.request.user.is_authenticated:
                form.instance.status_changed_by = self.request.user
        
        # Gestione speciale per richieste AJAX
        if is_ajax_status_update:
            from django.http import JsonResponse
            self.object = form.save()
            return JsonResponse({'success': True, 'status': form.instance.get_status_display()})
        
        # Messaggio di successo per richieste normali
        messages.success(self.request, _('Sotto-progetto aggiornato con successo!'))
        
        # Se è stato passato il parametro 'next' nell'URL, redirect a quella pagina
        if 'next' in self.request.GET:
            self.success_url = self.request.GET.get('next')
            
        return super().form_valid(form)
    
    def get_success_url(self):
        if hasattr(self, 'success_url') and self.success_url:
            return self.success_url
        
        # Se l'aggiornamento è stato solo per lo stato e siamo venuti dalla pagina del progetto
        referer = self.request.META.get('HTTP_REFERER', '')
        if 'status' in self.request.GET and '/projects/' in referer and '/subproject/' not in referer:
            project_id = self.object.project_id
            return reverse_lazy('projects:project_detail', kwargs={'pk': project_id})
            
        return reverse_lazy('projects:subproject_detail', kwargs={'pk': self.object.pk})

class SubProjectDeleteView(LoginRequiredMixin, DeleteView):
    model = SubProject
    template_name = 'projects/subproject_delete.html'
    
    def get_success_url(self):
        return reverse_lazy('projects:project_detail', kwargs={'pk': self.object.project.pk})
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Sotto-progetto eliminato con successo!'))
        return super().delete(request, *args, **kwargs)