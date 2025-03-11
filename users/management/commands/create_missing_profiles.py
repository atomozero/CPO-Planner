# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from users.models import UserProfile


class Command(BaseCommand):
    help = 'Crea profili utente per tutti gli utenti che non ne hanno uno'

    def handle(self, *args, **options):
        all_users = User.objects.all()
        count = 0
        
        for user in all_users:
            try:
                # Se il profilo esiste, passiamo al prossimo utente
                user.profile
            except User.profile.RelatedObjectDoesNotExist:
                # Crea un profilo se non esiste
                UserProfile.objects.create(user=user)
                count += 1
                self.stdout.write(self.style.SUCCESS(f'Creato profilo per l\'utente: {user.username}'))
        
        self.stdout.write(self.style.SUCCESS(f'Creati {count} nuovi profili utente'))