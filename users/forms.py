# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth.models import User
from .models import UserProfile


class UserUpdateForm(forms.ModelForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'dark_mode', 'receive_notifications', 'language', 
                  'company_name', 'phone_number', 'vat_number', 'address']
        labels = {
            'avatar': 'Immagine profilo',
            'dark_mode': 'Modalità scura',
            'receive_notifications': 'Ricevi notifiche',
            'language': 'Lingua',
            'company_name': 'Nome azienda',
            'phone_number': 'Numero di telefono',
            'vat_number': 'Partita IVA',
            'address': 'Indirizzo'
        }