# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('settings/', views.settings_view, name='settings'),
]