from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    # Abilita nuovamente projects per evitare dipendenze circolari
    path('projects/', include('projects.urls')),
    path('', include('cpo_core.urls')),
    path('financial/', include('financial.urls')),
    path('documenti/', include('cpo_planner.documents.urls')),
    path('report/', include('cpo_planner.reporting.urls', namespace='reporting')),
    path('environmental/', include('cpo_planner.environmental.urls')),
    path('mappa/', include('cpo_planner.mapping.urls')),
    path('users/', include('users.urls')),
    # Autenticazione
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html'), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(template_name='auth/password_reset_done.html'), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name='auth/password_reset_confirm.html'), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name='auth/password_reset_complete.html'), 
         name='password_reset_complete'),
    # Per compatibilità con il valore predefinito di LoginRequiredMixin
    path('accounts/login/', lambda request: redirect('/login/'), name='account_login'),
    path('infrastructure/', include('infrastructure.urls')),

]

# Servire i file statici e media in ambiente di sviluppo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)