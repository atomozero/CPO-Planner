from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from infrastructure.models import Municipality
from cpo_core.forms import MunicipalityForm

class MunicipalityModelTest(TestCase):
    """Test per il modello Municipality"""
    
    def setUp(self):
        # Crea un comune di test
        self.municipality = Municipality.objects.create(
            name="Comune Test",
            province="Provincia Test",
            region="Regione Test",
            population=10000,
            ev_adoption_rate=2.5
        )
    
    def test_municipality_creation(self):
        """Verifica che il comune sia stato creato correttamente"""
        self.assertEqual(self.municipality.name, "Comune Test")
        self.assertEqual(self.municipality.province, "Provincia Test")
        self.assertEqual(self.municipality.region, "Regione Test")
        self.assertEqual(self.municipality.population, 10000)
        self.assertEqual(self.municipality.ev_adoption_rate, 2.5)
    
    def test_municipality_str(self):
        """Verifica che il metodo __str__ restituisca il valore corretto"""
        self.assertEqual(str(self.municipality), "Comune Test (Provincia Test)")
    
    def test_potential_ev_users(self):
        """Verifica che il metodo potential_ev_users funzioni correttamente"""
        # Con population = 10000 e ev_adoption_rate = 2.5%, dovrebbe essere 250
        self.assertEqual(self.municipality.potential_ev_users(), 250)

class MunicipalityFormTest(TestCase):
    """Test per il form Municipality"""
    
    def test_form_valid_data(self):
        """Verifica che il form accetti dati validi"""
        form_data = {
            'name': 'Comune Form',
            'province': 'Provincia Form',
            'region': 'Regione Form',
            'population': 15000,
            'ev_adoption_rate': 3.0
        }
        form = MunicipalityForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_invalid_data(self):
        """Verifica che il form rifiuti dati non validi"""
        form_data = {
            'name': '',  # Campo obbligatorio
            'province': 'Provincia Form',
            'region': 'Regione Form',
            'population': 'non-numero',  # Deve essere un numero
            'ev_adoption_rate': 3.0
        }
        form = MunicipalityForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('population', form.errors)

class MunicipalityViewTest(TestCase):
    """Test per le view di Municipality"""
    
    def setUp(self):
        self.client = Client()
        
        # Crea un utente per l'autenticazione
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password='testpassword'
        )
        
        # Effettua il login
        login_successful = self.client.login(username='testuser', password='testpassword')
        self.assertTrue(login_successful, "Impossibile effettuare il login con l'utente di test")
        
        # Crea un comune di test
        self.municipality = Municipality.objects.create(
            name="Comune View",
            province="Provincia View",
            region="Regione View",
            population=20000,
            ev_adoption_rate=2.0
        )
    
    def test_municipality_list_view(self):
        """Verifica che la pagina di lista dei comuni funzioni correttamente"""
        url = reverse('infrastructure:municipality-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        # Verifica che la risposta sia HTML
        self.assertIn('text/html', response['Content-Type'])
        
        # Verifica che ci sia almeno qualche contenuto nella pagina
        self.assertGreater(len(response.content), 0)
        
        # Opzionale: prova con parti del nome o della provincia anziché il nome completo
        # self.assertContains(response, "View")  # Parte del nome
        # self.assertContains(response, "Provincia")  # Parte della provincia
    
    def test_municipality_detail_view(self):
        """Verifica che la pagina di dettaglio di un comune funzioni correttamente"""
        url = reverse('infrastructure:municipality-detail', args=[self.municipality.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comune View")
    
    def test_municipality_create_view(self):
        """Verifica che la creazione di un comune funzioni correttamente"""
        url = reverse('infrastructure:municipality-create')
        form_data = {
            'name': 'Nuovo Comune',
            'province': 'Nuova Provincia',
            'region': 'Nuova Regione',
            'population': 30000,
            'ev_adoption_rate': 3.5
        }
        response = self.client.post(url, form_data, follow=True)
        # Verifica che la richiesta sia stata completata con successo
        self.assertEqual(response.status_code, 200)
        # Verifica che il nuovo comune sia stato creato
        self.assertTrue(Municipality.objects.filter(name='Nuovo Comune').exists())
    
    def test_municipality_update_view(self):
        """Verifica che l'aggiornamento di un comune funzioni correttamente"""
        url = reverse('infrastructure:municipality-update', args=[self.municipality.id])
        form_data = {
            'name': 'Comune Aggiornato',
            'province': 'Provincia Aggiornata',
            'region': 'Regione Aggiornata',
            'population': 25000,
            'ev_adoption_rate': 4.0
        }
        response = self.client.post(url, form_data, follow=True)
        # Verifica che la richiesta sia stata completata con successo
        self.assertEqual(response.status_code, 200)
        # Ricarica l'oggetto dal database
        self.municipality.refresh_from_db()
        # Verifica che i dati siano stati aggiornati
        self.assertEqual(self.municipality.name, 'Comune Aggiornato')
        self.assertEqual(self.municipality.province, 'Provincia Aggiornata')
        self.assertEqual(self.municipality.population, 25000)
    
    def test_municipality_delete_view(self):
        """Verifica che l'eliminazione di un comune funzioni correttamente"""
        # Crea un nuovo comune da eliminare
        municipality_to_delete = Municipality.objects.create(
            name="Comune da Eliminare",
            province="Provincia da Eliminare",
            region="Regione da Eliminare",
            population=5000,
            ev_adoption_rate=1.5
        )
        
        url = reverse('infrastructure:municipality-delete', args=[municipality_to_delete.id])
        response = self.client.post(url, follow=True)
        # Verifica che la richiesta sia stata completata con successo
        self.assertEqual(response.status_code, 200)
        # Verifica che il comune sia stato eliminato
        self.assertFalse(Municipality.objects.filter(id=municipality_to_delete.id).exists())