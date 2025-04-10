# cpo_planner/projects/models/financial.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from projects.models import Project
from .charging_station import ChargingStation

class FinancialParameters(models.Model):
    """Parametri finanziari globali per il calcolo del ROI e delle previsioni finanziarie"""
    
    project = models.OneToOneField(
        Project, 
        on_delete=models.CASCADE, 
        related_name='financial_parameters',
        verbose_name=_('Progetto')
    )
    
    # Parametri generali
    investment_years = models.PositiveIntegerField(
        _('Durata investimento (anni)'),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(20)],
        help_text=_("Durata dell'investimento in anni")
    )
    
    # Parametri del prestito
    loan_amount = models.DecimalField(
        _('Importo prestito'),
        max_digits=12, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Importo del prestito in €")
    )
    loan_interest_rate = models.DecimalField(
        _('Tasso interesse prestito'),
        max_digits=5, 
        decimal_places=2, 
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        help_text=_("Tasso di interesse annuale del prestito in %")
    )
    loan_term = models.PositiveIntegerField(
        _('Durata prestito (anni)'),
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(30)],
        help_text=_("Durata del prestito in anni")
    )
    pre_amortization_years = models.PositiveIntegerField(
        _('Anni preammortamento'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text=_("Anni di preammortamento del prestito (opzionale)")
    )
    
    # Parametri di mercato
    market_growth_rate = models.DecimalField(
        _('Tasso crescita mercato EV'),
        max_digits=5, 
        decimal_places=2, 
        default=20.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Tasso di crescita annuale del mercato EV in %")
    )
    inflation_rate = models.DecimalField(
        _('Tasso inflazione'),
        max_digits=5, 
        decimal_places=2, 
        default=2.0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        help_text=_("Tasso di inflazione annuale in %")
    )
    
    # Parametri operativi
    maintenance_cost_percentage = models.DecimalField(
        _('Costo manutenzione %'),
        max_digits=5, 
        decimal_places=2, 
        default=5.0,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        help_text=_("Costo di manutenzione annuale come % dell'investimento iniziale")
    )
    energy_price_increase_rate = models.DecimalField(
        _('Aumento annuo prezzo energia'),
        max_digits=5, 
        decimal_places=2, 
        default=3.0,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        help_text=_("Tasso di aumento annuale del prezzo dell'energia in %")
    )
    charging_price_increase_rate = models.DecimalField(
        _('Aumento annuo prezzo ricarica'),
        max_digits=5, 
        decimal_places=2, 
        default=1.5,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        help_text=_("Tasso di aumento annuale del prezzo di ricarica in %")
    )
    
    # Parametri di fallimento/exit
    failure_probability = models.DecimalField(
        _('Probabilità guasto annuale'),
        max_digits=5, 
        decimal_places=2, 
        default=1.0,
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        help_text=_("Probabilità annuale di guasto di una colonnina in %")
    )
    repair_cost_percentage = models.DecimalField(
        _('Costo riparazione %'),
        max_digits=5, 
        decimal_places=2, 
        default=10.0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Costo medio di riparazione come % del costo della colonnina")
    )
    
    created_at = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Data aggiornamento'), auto_now=True)
    
    def __str__(self):
        return _("Parametri finanziari per %(project)s") % {'project': self.project.name}
    
    class Meta:
        verbose_name = _("Parametri finanziari")
        verbose_name_plural = _("Parametri finanziari")


class FinancialAnalysis(models.Model):
    """Risultati dell'analisi finanziaria per un progetto o una stazione"""
    
    project = models.OneToOneField(
        Project, 
        on_delete=models.CASCADE, 
        related_name='financial_analysis',
        null=True, blank=True,
        verbose_name=_('Progetto')
    )
    
    charging_station = models.OneToOneField(
        ChargingStation, 
        on_delete=models.CASCADE, 
        related_name='financial_analysis',
        null=True, blank=True,
        verbose_name=_('Stazione di ricarica')
    )
    
    # Metriche finanziarie
    total_investment = models.DecimalField(
        _('Investimento totale'),
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Investimento totale iniziale in €")
    )
    net_present_value = models.DecimalField(
        _('Valore attuale netto'),
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Valore attuale netto (NPV) in €")
    )
    internal_rate_of_return = models.DecimalField(
        _('Tasso interno di rendimento'),
        max_digits=6, 
        decimal_places=2, 
        default=0,
        help_text=_("Tasso interno di rendimento (IRR) in %")
    )
    payback_period = models.DecimalField(
        _('Periodo di recupero'),
        max_digits=5, 
        decimal_places=2, 
        default=0,
        help_text=_("Periodo di recupero dell'investimento in anni")
    )
    return_on_investment = models.DecimalField(
        _('ROI'),
        max_digits=6, 
        decimal_places=2, 
        default=0,
        help_text=_("Ritorno sull'investimento (ROI) in %")
    )
    profitability_index = models.DecimalField(
        _('Indice di redditività'),
        max_digits=6, 
        decimal_places=2, 
        default=0,
        help_text=_("Indice di redditività (PI)")
    )
    
    # Risultati aggregati
    total_revenue = models.DecimalField(
        _('Ricavi totali'),
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Ricavi totali nel periodo di investimento in €")
    )
    total_costs = models.DecimalField(
        _('Costi totali'),
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Costi totali nel periodo di investimento in €")
    )
    total_profit = models.DecimalField(
        _('Profitto totale'),
        max_digits=12, 
        decimal_places=2, 
        default=0,
        help_text=_("Profitto totale nel periodo di investimento in €")
    )
    
    # Dati JSON per grafici e tabelle dettagliate
    yearly_cash_flow = models.JSONField(
        _('Flussi di cassa annuali'),
        default=dict,
        help_text=_("Flussi di cassa annuali in formato JSON")
    )
    monthly_cash_flow = models.JSONField(
        _('Flussi di cassa mensili'),
        default=dict,
        help_text=_("Flussi di cassa mensili in formato JSON (primi 24 mesi)")
    )
    loan_schedule = models.JSONField(
        _('Piano ammortamento prestito'),
        default=dict,
        help_text=_("Piano di ammortamento del prestito in formato JSON")
    )
    failure_simulation = models.JSONField(
        _('Simulazione guasti'),
        default=dict,
        help_text=_("Simulazione di guasti e riparazioni in formato JSON")
    )
    
    created_at = models.DateTimeField(_('Data creazione'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Data aggiornamento'), auto_now=True)
    
    def __str__(self):
        if self.project:
            return _("Analisi finanziaria per progetto %(project)s") % {'project': self.project.name}
        else:
            return _("Analisi finanziaria per stazione %(station)s") % {'station': self.charging_station.name}
    
    class Meta:
        verbose_name = _("Analisi finanziaria")
        verbose_name_plural = _("Analisi finanziarie")
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(project__isnull=False, charging_station__isnull=True) | 
                    models.Q(project__isnull=True, charging_station__isnull=False)
                ),
                name="financial_analysis_project_or_station"
            )
        ]
