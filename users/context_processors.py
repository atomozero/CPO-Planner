# -*- coding: utf-8 -*-
def user_avatar(request):
    """
    Aggiunge l'URL dell'avatar utente al contesto di tutti i template.
    Se l'utente non ha un avatar, restituisce None.
    """
    if request.user.is_authenticated:
        try:
            if request.user.profile.avatar and request.user.profile.avatar.url:
                return {'user_avatar_url': request.user.profile.avatar.url}
        except:
            pass
    return {'user_avatar_url': None}