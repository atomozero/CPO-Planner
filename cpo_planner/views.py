from django.shortcuts import render

def handler404(request, exception):
    """
    Gestisce le pagine non trovate (404)
    """
    return render(request, 'errors/404.html', status=404)

def handler500(request):
    """
    Gestisce gli errori del server (500)
    """
    return render(request, 'errors/500.html', status=500)

def handler403(request, exception):
    """
    Gestisce gli errori di accesso negato (403)
    """
    return render(request, 'errors/403.html', status=403)