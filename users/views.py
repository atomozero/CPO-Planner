# -*- coding: utf-8 -*-
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from .forms import UserUpdateForm, ProfileUpdateForm
from cpo_core.models import Project, ChargingStation


@login_required
def profile_view(request):
    # Verifica e crea il profilo se non esiste
    try:
        profile = request.user.profile
    except:
        from users.models import UserProfile
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Il tuo profilo è stato aggiornato con successo!')
            return redirect('users:profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)
    
    # Raccolta statistiche utente
    statistics = {
        'projects_count': Project.objects.filter(project_manager=request.user).count(),
        'stations_count': ChargingStation.objects.filter(subproject__project__project_manager=request.user).count(),
    }
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'statistics': statistics
    }
    
    return render(request, 'users/profile.html', context)


@login_required
def settings_view(request):
    # Verifica e crea il profilo se non esiste
    try:
        profile = request.user.profile
    except:
        from users.models import UserProfile
        profile = UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, 'Le tue impostazioni sono state aggiornate con successo!')
            return redirect('users:settings')
    else:
        profile_form = ProfileUpdateForm(instance=profile)
    
    context = {
        'profile_form': profile_form,
    }
    
    return render(request, 'users/settings.html', context)