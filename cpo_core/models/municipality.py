# Importa il modello Municipality da infrastructure.models
from infrastructure.models import Municipality

# Definisci la funzione municipality_logo_path necessaria per le migrazioni
def municipality_logo_path(instance, filename):
    # Restituisce il percorso dove salvare i logo dei comuni
    return f"municipality_logos/{instance.name}_{filename}"

# Questo file esiste solo per garantire la retrocompatibilità con le migrazioni esistenti