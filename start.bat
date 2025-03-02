@echo off
echo Creazione progetto CPO Planner per operatori di stazioni di ricarica...

REM Creazione directory principale e ambiente virtuale
echo Creazione ambiente virtuale Python...
python -m venv venv
call venv\Scripts\activate

REM Installazione dipendenze
echo Installazione Django e dipendenze...
pip install django
pip install numpy pandas matplotlib reportlab django-crispy-forms pillow

REM Creazione del progetto Django
echo Creazione del progetto Django...
django-admin startproject cpo_planner .

REM Creazione delle app Django
echo Creazione delle app Django...
python manage.py startapp core
python manage.py startapp financial
python manage.py startapp project_management
python manage.py startapp station_planning
python manage.py startapp reporting
python manage.py startapp solar_integration

REM Creazione struttura directory aggiuntiva
echo Creazione della struttura di directory...
mkdir static
mkdir static\css
mkdir static\js
mkdir static\img
mkdir templates
mkdir templates\base
mkdir media
mkdir media\reports

REM Aggiunta delle app al settings.py
echo Configurazione settings.py...
echo.>> cpo_planner\settings.py
echo # Applicazioni installate per CPO Planner >> cpo_planner\settings.py
echo INSTALLED_APPS += [ >> cpo_planner\settings.py
echo     'core', >> cpo_planner\settings.py
echo     'financial', >> cpo_planner\settings.py
echo     'project_management', >> cpo_planner\settings.py
echo     'station_planning', >> cpo_planner\settings.py
echo     'reporting', >> cpo_planner\settings.py
echo     'solar_integration', >> cpo_planner\settings.py
echo     'crispy_forms', >> cpo_planner\settings.py
echo ] >> cpo_planner\settings.py
echo. >> cpo_planner\settings.py
echo CRISPY_TEMPLATE_PACK = 'bootstrap4' >> cpo_planner\settings.py
echo. >> cpo_planner\settings.py
echo # Configurazione media e static files >> cpo_planner\settings.py
echo MEDIA_URL = '/media/' >> cpo_planner\settings.py
echo MEDIA_ROOT = os.path.join(BASE_DIR, 'media') >> cpo_planner\settings.py
echo. >> cpo_planner\settings.py
echo STATICFILES_DIRS = [ >> cpo_planner\settings.py
echo     os.path.join(BASE_DIR, 'static'), >> cpo_planner\settings.py
echo ] >> cpo_planner\settings.py

REM Creazione requirements.txt
echo Creazione file requirements.txt...
echo django>=4.0,<5.0 > requirements.txt
echo numpy >> requirements.txt
echo pandas >> requirements.txt
echo matplotlib >> requirements.txt
echo reportlab >> requirements.txt
echo django-crispy-forms >> requirements.txt
echo pillow >> requirements.txt
echo openpyxl >> requirements.txt

REM Creazione file di base per il core
echo Creazione file di base per i modelli...
echo from django.db import models > core\models.py
echo from django.contrib.auth.models import User >> core\models.py
echo from django.utils import timezone >> core\models.py
echo import uuid >> core\models.py
echo. >> core\models.py
echo # I modelli core verranno implementati qui >> core\models.py

echo Creazione file di base per i modelli finanziari...
echo from django.db import models > financial\models.py
echo from django.utils import timezone >> financial\models.py
echo from core.models import Project, SubProject, ChargingStation >> financial\models.py
echo. >> financial\models.py
echo # I modelli finanziari verranno implementati qui >> financial\models.py

REM Creazione gitignore
echo Creazione .gitignore...
echo # Python > .gitignore
echo __pycache__/ >> .gitignore
echo *.py[cod] >> .gitignore
echo *$py.class >> .gitignore 
echo *.so >> .gitignore
echo .Python >> .gitignore
echo venv/ >> .gitignore
echo ENV/ >> .gitignore
echo env/ >> .gitignore
echo .venv/ >> .gitignore
echo. >> .gitignore
echo # Django >> .gitignore
echo *.log >> .gitignore
echo *.pot >> .gitignore
echo *.pyc >> .gitignore
echo db.sqlite3 >> .gitignore
echo db.sqlite3-journal >> .gitignore
echo media >> .gitignore
echo. >> .gitignore
echo # IDE >> .gitignore
echo .idea/ >> .gitignore
echo .vscode/ >> .gitignore
echo *.swp >> .gitignore
echo *.swo >> .gitignore

REM Creazione README.md
echo Creazione README.md...
echo # CPO Planner > README.md
echo. >> README.md
echo Sistema di pianificazione, progettazione e gestione per operatori di punti di ricarica (CPO) per veicoli elettrici. >> README.md
echo. >> README.md
echo ## Funzionalità >> README.md
echo. >> README.md
echo - Analisi finanziaria e previsioni >> README.md
echo - Business plan per progetti di installazione >> README.md
echo - Organizzazione strutturata dei progetti >> README.md
echo - Reportistica dettagliata >> README.md
echo - Integrazione con impianti fotovoltaici >> README.md
echo. >> README.md
echo ## Installazione >> README.md
echo. >> README.md
echo 1. Clona il repository >> README.md
echo 2. Crea un ambiente virtuale: `python -m venv venv` >> README.md
echo 3. Attiva l'ambiente virtuale: >> README.md
echo    - Windows: `venv\Scripts\activate` >> README.md
echo    - Linux/Mac: `source venv/bin/activate` >> README.md
echo 4. Installa le dipendenze: `pip install -r requirements.txt` >> README.md
echo 5. Esegui le migrazioni: `python manage.py migrate` >> README.md
echo 6. Crea un superuser: `python manage.py createsuperuser` >> README.md
echo 7. Avvia il server: `python manage.py runserver` >> README.md

echo Setup completato con successo! Ora puoi sviluppare il tuo progetto CPO Planner.
echo Per avviare il server di sviluppo: python manage.py runserver
echo Ricorda di eseguire 'python manage.py makemigrations' e 'python manage.py migrate' per creare il database.
echo Per creare un superuser: python manage.py createsuperuser

cd ..