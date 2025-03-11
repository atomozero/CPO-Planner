$(document).ready(function() {
    // Funzione per mostrare/nascondere i campi in base al tipo di tariffa
    function updateFieldsVisibility() {
        var tariffType = $('#id_tariff_type').val();
        
        if (tariffType === 'fixed') {
            // Mostra i campi per tariffa fissa, nascondi quelli per PUN
            $('#fixed-price-section').show();
            $('#pun-price-section').hide();
        } else if (tariffType === 'pun') {
            // Mostra i campi per PUN, nascondi quelli per tariffa fissa
            $('#fixed-price-section').hide();
            $('#pun-price-section').show();
        } else {
            // Fallback: mostra tutti i campi
            $('#fixed-price-section').show();
            $('#pun-price-section').show();
        }
        
        console.log("Tipo tariffa selezionato:", tariffType);
        console.log("Sezione fixed-price visibile:", $('#fixed-price-section').is(":visible"));
        console.log("Sezione pun-price visibile:", $('#pun-price-section').is(":visible"));
    }
    
    // Esegui al caricamento della pagina
    setTimeout(function() {
        updateFieldsVisibility();
    }, 100); // Piccolo ritardo per assicurarsi che il DOM sia completamente caricato
    
    // Esegui quando cambia il tipo di tariffa
    $('#id_tariff_type').change(function() {
        updateFieldsVisibility();
    });
    
    // Aggiungi sezione informativa su PUN
    if ($('#id_tariff_type').length) {
        var punInfoHtml = `
        <div class="alert alert-info mt-3" id="pun-info" style="display:none;">
            <h5><i class="fas fa-info-circle mr-2"></i>Tariffe indicizzate PUN</h5>
            <p>Le tariffe indicizzate al PUN (Prezzo Unico Nazionale) utilizzano il prezzo di riferimento dell'energia dal Mercato Elettrico, variabile per fascia oraria:</p>
            <ul>
                <li><strong>F1 (Ore di punta)</strong>: Lunedì-Venerdì, 8:00-19:00 (esclusi festivi)</li>
                <li><strong>F2 (Ore intermedie)</strong>: Lunedì-Venerdì, 7:00-8:00 e 19:00-23:00, Sabato 7:00-23:00</li>
                <li><strong>F3 (Ore fuori punta)</strong>: Lunedì-Sabato, 23:00-7:00, Domenica e festivi</li>
            </ul>
            <p>Lo "spread" è il costo aggiuntivo applicato al PUN per coprire oneri di sistema, dispacciamento, etc.</p>
        </div>`;
        
        $('#id_tariff_type').closest('.form-group').after(punInfoHtml);
        
        // Mostra/nascondi info PUN quando cambia il tipo di tariffa
        function updatePunInfo() {
            if ($('#id_tariff_type').val() === 'pun') {
                $('#pun-info').slideDown();
            } else {
                $('#pun-info').slideUp();
            }
        }
        
        updatePunInfo();
        $('#id_tariff_type').change(updatePunInfo);
    }
    
    // Aggiungi un pulsante per forzare l'aggiornamento della visualizzazione
    // (utile per risolvere problemi in caso il toggle automatico non funzioni)
    $('<button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="toggle-sections">Aggiorna visualizzazione campi</button>')
        .insertAfter('#id_tariff_type')
        .click(function(e) {
            e.preventDefault();
            updateFieldsVisibility();
        });
});