# CPO Planner

Un sistema open source completo per la pianificazione, progettazione e gestione di infrastrutture di ricarica per veicoli elettrici, pensato per i Charge Point Operator (CPO).

## 🔋 Panoramica

CPO Planner è una piattaforma web basata su Django che aiuta gli operatori di stazioni di ricarica a pianificare, valutare e monitorare la redditività delle loro infrastrutture. La piattaforma fornisce analisi finanziarie dettagliate, simulazioni, e supporto decisionale con un'attenzione particolare alla sostenibilità ambientale.

### Caratteristiche Principali

- 📊 **Analisi finanziaria completa**: ROI, utili mensili/annuali, flussi di cassa, esposizione bancaria
- 💼 **Business plan automatizzati**: per progetti completi e singole stazioni
- 🏙️ **Organizzazione per comune**: struttura gerarchica per progetti e sotto-progetti
- 🔌 **Gestione dettagliata delle stazioni**: costi, ROI, aspetti tecnici
- ☀️ **Integrazione fotovoltaico**: calcolo della sostenibilità e ritorno economico
- 📝 **Reportistica avanzata**: documentazione completa stampabile per comuni e stakeholder
- ⏱️ **Cronoprogramma**: strumenti di pianificazione temporale e monitoraggio
- 🛣️ **Exit strategy**: simulazione di scenari di uscita e analisi di resilienza

## 🛠️ Tecnologie

- [Django](https://www.djangoproject.com/) - Framework web
- [Pandas](https://pandas.pydata.org/) - Analisi dati e calcoli finanziari
- [ReportLab](https://www.reportlab.com/) - Generazione di report PDF
- [Matplotlib](https://matplotlib.org/) - Visualizzazione dati
- [Bootstrap](https://getbootstrap.com/) - UI/UX

## 🚀 Installazione

```bash
# Clona il repository
git clone https://github.com/yourusername/cpo-planner.git
cd cpo-planner

# Crea e attiva l'ambiente virtuale
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Installa le dipendenze
pip install -r requirements.txt

# Esegui le migrazioni del database
python manage.py migrate

# Crea un superuser
python manage.py createsuperuser

# Avvia il server
python manage.py runserver
```

## 📱 Funzionalità

### Analisi Finanziaria
- Calcolo dettagliato del ROI per progetto e per stazione
- Previsione di utili mensili, annuali e totali
- Simulazione di flussi di cassa su 10+ anni
- Modellazione dell'esposizione bancaria con opzione preammortamento

### Pianificazione Strategica
- Previsioni di mercato EV fino al 2030
- Simulazione di scenari di utilizzo e crescita
- Analisi di sensibilità per fattori chiave (prezzi energia, tassi di utilizzo)
- Valutazione di exit strategy in caso di criticità

### Supporto Operativo
- Simulazione di guasti casuali delle stazioni
- Calcolo dei costi di manutenzione
- Ottimizzazione delle tariffe di ricarica
- Analisi degli indicatori di performance

### Integrazione Fotovoltaico
- Valutazione della sostenibilità di impianti solari
- Calcolo dell'autoconsumo e della riduzione dei costi
- ROI specifico per l'impianto fotovoltaico
- Benefici ambientali (CO2 evitata)

## 📁 Struttura del Progetto

```
cpo_planner/
│
├── core/                # Modelli e funzionalità di base
├── financial/           # Analisi finanziaria e calcoli
├── project_management/  # Gestione progetti e sotto-progetti
├── station_planning/    # Pianificazione stazioni di ricarica
├── reporting/           # Generazione di report e documenti
├── solar_integration/   # Integrazione impianti fotovoltaici
│
├── static/              # File statici (CSS, JS, immagini)
└── templates/           # Template HTML
```

## 🤝 Contribuire

Le contribuzioni sono benvenute! Per favore leggi le [linee guida per contribuire](CONTRIBUTING.md) prima di iniziare.

1. Fai un fork del repository
2. Crea un branch per la tua feature (`git checkout -b feature/amazing-feature`)
3. Commit delle tue modifiche (`git commit -m 'Aggiunta una nuova funzionalità'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

## 📜 Licenza

Questo progetto è distribuito con licenza MIT. Vedi il file [LICENSE](LICENSE) per maggiori dettagli.

## 📊 Casi d'Uso

- **CPO emergenti**: valutazione della redditività di nuove infrastrutture
- **Pianificatori urbani**: analisi di reti di ricarica comunali
- **Investitori**: valutazione di opportunità nel settore EV
- **Utility**: pianificazione dell'espansione della rete di ricarica
