/**
 * Inizializzazione e gestione della mappa interattiva
 */

// Variabili globali
let map;
let stationsSource = { type: 'FeatureCollection', features: [] };
let markersSource = { type: 'FeatureCollection', features: [] };
let visibleStations = [];
let mapboxDraw;
let mapConfig;

/**
 * Inizializza la mappa con le configurazioni fornite
 * @param {Object} config - Configurazione della mappa
 */
function initMap(config) {
    mapConfig = config;
    
    // Imposta l'API key di Mapbox
    mapboxgl.accessToken = config.apiKey;
    
    // Crea l'istanza della mappa
    map = new mapboxgl.Map({
        container: 'map',
        style: `mapbox://styles/mapbox/${config.mapStyle}`,
        center: config.defaultCenter,
        zoom: config.defaultZoom,
        attributionControl: true
    });
    
    // Aggiunge i controlli
    map.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.addControl(new mapboxgl.FullscreenControl(), 'top-right');
    map.addControl(new mapboxgl.GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true
    }), 'top-right');
    
    // Aggiunge il geocoder per la ricerca di luoghi
    const geocoder = new MapboxGeocoder({
        accessToken: mapboxgl.accessToken,
        mapboxgl: mapboxgl,
        placeholder: 'Cerca un luogo...',
        countries: 'it',
        language: 'it'
    });
    map.addControl(geocoder, 'top-left');
    
    // Inizializza il disegno sulla mappa
    mapboxDraw = new MapboxDraw({
        displayControlsDefault: false,
        controls: {
            point: true,
            trash: true
        }
    });
    map.addControl(mapboxDraw, 'top-left');
    
    // Disabilita il disegno di default
    document.querySelector('.mapbox-gl-draw_point').style.display = 'none';
    document.querySelector('.mapbox-gl-draw_trash').style.display = 'none';
    
    // Quando la mappa è pronta...
    map.on('load', function() {
        // Aggiunge le sorgenti di dati
        map.addSource('stations', {
            type: 'geojson',
            data: stationsSource,
            cluster: config.showClusters,
            clusterMaxZoom: 14,
            clusterRadius: 50,
            clusterMinPoints: config.minClusterSize
        });
        
        map.addSource('markers', {
            type: 'geojson',
            data: markersSource
        });
        
        // Aggiunge i layer per i clusters
        map.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'stations',
            filter: ['has', 'point_count'],
            paint: {
                'circle-color': [
                    'step',
                    ['get', 'point_count'],
                    '#51bbd6',  // 0-9 stazioni
                    10,
                    '#f1f075',  // 10-49 stazioni
                    50,
                    '#f28cb1'   // 50+ stazioni
                ],
                'circle-radius': [
                    'step',
                    ['get', 'point_count'],
                    20,         // Raggio per 0-9 stazioni
                    10,
                    30,         // Raggio per 10-49 stazioni
                    50,
                    40          // Raggio per 50+ stazioni
                ]
            }
        });
        
        // Aggiunge il layer per i numeri dei cluster
        map.addLayer({
            id: 'cluster-count',
            type: 'symbol',
            source: 'stations',
            filter: ['has', 'point_count'],
            layout: {
                'text-field': '{point_count_abbreviated}',
                'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
                'text-size': 12
            },
            paint: {
                'text-color': '#ffffff'
            }
        });
        
        // Aggiunge il layer per le stazioni singole
        map.addLayer({
            id: 'unclustered-point',
            type: 'circle',
            source: 'stations',
            filter: ['!', ['has', 'point_count']],
            paint: {
                'circle-color': [
                    'match',
                    ['get', 'status'],
                    'planned', '#4e73df',          // Blu per pianificate
                    'under_construction', '#f6c23e', // Giallo per in costruzione
                    'operational', '#1cc88a',      // Verde per operative
                    'maintenance', '#f8f9fc',      // Grigio chiaro per manutenzione
                    'offline', '#e74a3b',          // Rosso per offline
                    '#4e73df'                       // Default
                ],
                'circle-radius': 8,
                'circle-stroke-width': 1,
                'circle-stroke-color': '#fff'
            }
        });
        
        // Aggiunge il layer per i marker personalizzati
        map.addLayer({
            id: 'custom-markers',
            type: 'symbol',
            source: 'markers',
            layout: {
                'icon-image': ['concat', ['get', 'icon'], '-15'],
                'icon-allow-overlap': true,
                'text-field': ['get', 'name'],
                'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
                'text-offset': [0, 1.25],
                'text-anchor': 'top',
                'text-size': 12,
                'text-optional': true
            },
            paint: {
                'text-color': '#000000',
                'text-halo-color': '#ffffff',
                'text-halo-width': 1
            }
        });
        
        // Carica i dati iniziali
        loadStations();
        loadMarkers();
        
        // Se è una mappa salvata, carica i suoi dati
        if (config.savedMapId) {
            loadSavedMap(config.savedMapId);
        }
        // Altrimenti, se ci sono filtri preimpostati, li applica
        else if (config.projectFilter || config.subprojectFilter) {
            if (config.projectFilter) {
                document.getElementById('projectFilter').value = config.projectFilter;
            }
            if (config.subprojectFilter) {
                document.getElementById('subprojectFilter').value = config.subprojectFilter;
            }
            applyFilters();
        }
        
        // Popup al click su una stazione
        map.on('click', 'unclustered-point', function(e) {
            const coordinates = e.features[0].geometry.coordinates.slice();
            const props = e.features[0].properties;
            
            // Contenuto HTML del popup
            const html = `
                <div class="map-popup">
                    <h5>${props.name}</h5>
                    <p><strong>Indirizzo:</strong> ${props.address || 'N/D'}</p>
                    <p><strong>Stato:</strong> <span class="badge ${getStatusBadgeClass(props.status)}">${props.status_display}</span></p>
                    <p><strong>Potenza:</strong> ${props.power} kW</p>
                    <p><strong>Punti di ricarica:</strong> ${props.charging_points}</p>
                    <p><strong>Connettori:</strong> ${props.connectors}</p>
                    ${props.installation_date ? `<p><strong>Data installazione:</strong> ${props.installation_date}</p>` : ''}
                    ${props.project_name ? `<p><strong>Progetto:</strong> ${props.project_name}</p>` : ''}
                    ${props.subproject_name ? `<p><strong>Sotto-progetto:</strong> ${props.subproject_name}</p>` : ''}
                    <a href="/projects/charging-stations/${props.id}/" class="btn btn-primary btn-sm">Dettagli</a>
                </div>
            `;
            
            // Previene spostamento del popup durante lo zoom
            while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
            }
            
            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(html)
                .addTo(map);
        });
        
        // Popup al click su un marker personalizzato
        map.on('click', 'custom-markers', function(e) {
            const coordinates = e.features[0].geometry.coordinates.slice();
            const props = e.features[0].properties;
            
            // Contenuto HTML del popup
            let html = `
                <div class="map-popup">
                    ${props.popup_title ? `<h5>${props.popup_title}</h5>` : `<h5>${props.name}</h5>`}
                    ${props.popup_content ? `<div>${props.popup_content}</div>` : ''}
                    ${props.description ? `<p>${props.description}</p>` : ''}
                `;
                
            // Aggiunge link al progetto/sotto-progetto se presenti
            if (props.project_name) {
                html += `<p><strong>Progetto:</strong> ${props.project_name}</p>`;
            }
            if (props.subproject_name) {
                html += `<p><strong>Sotto-progetto:</strong> ${props.subproject_name}</p>`;
            }
            
            // Aggiunge bottoni di modifica/elimina se è il proprio marker
            if (props.is_own_marker) {
                html += `
                    <div class="mt-2">
                        <a href="/mappa/marker/${props.id}/modifica/" class="btn btn-primary btn-sm">Modifica</a>
                        <a href="/mappa/marker/${props.id}/elimina/" class="btn btn-danger btn-sm ml-2">Elimina</a>
                    </div>
                `;
            }
            
            html += `</div>`;
            
            // Previene spostamento del popup durante lo zoom
            while (Math.abs(e.lngLat.lng - coordinates[0]) > 180) {
                coordinates[0] += e.lngLat.lng > coordinates[0] ? 360 : -360;
            }
            
            new mapboxgl.Popup()
                .setLngLat(coordinates)
                .setHTML(html)
                .addTo(map);
        });
        
        // Cambia il cursore sul hover 
        map.on('mouseenter', 'unclustered-point', function() {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'unclustered-point', function() {
            map.getCanvas().style.cursor = '';
        });
        map.on('mouseenter', 'custom-markers', function() {
            map.getCanvas().style.cursor = 'pointer';
        });
        map.on('mouseleave', 'custom-markers', function() {
            map.getCanvas().style.cursor = '';
        });
        
        // Zoom al click su cluster
        map.on('click', 'clusters', function(e) {
            const features = map.queryRenderedFeatures(e.point, { layers: ['clusters'] });
            const clusterId = features[0].properties.cluster_id;
            
            map.getSource('stations').getClusterExpansionZoom(clusterId, function(err, zoom) {
                if (err) return;
                
                map.easeTo({
                    center: features[0].geometry.coordinates,
                    zoom: zoom
                });
            });
        });
        
        // Gestore create per il disegno
        map.on('draw.create', function(e) {
            // Ottiene le coordinate del punto disegnato
            const point = e.features[0];
            const coords = point.geometry.coordinates;
            
            // Reindirizza alla pagina per creare un nuovo marker con le coordinate preimpostate
            window.location.href = `${config.addMarkerUrl}?lat=${coords[1]}&lng=${coords[0]}`;
        });
    });
    
    // Inizializza i gestori degli eventi
    initEventHandlers();
}

/**
 * Carica le stazioni dalla API
 */
function loadStations() {
    // Prepara i parametri della query
    const form = document.getElementById('mapFilterForm');
    const formData = new FormData(form);
    
    // Costruisce la query string
    let queryParams = new URLSearchParams();
    
    for (const [key, value] of formData.entries()) {
        // Gestisce i checkbox multipli
        if (key.endsWith('[]')) {
            queryParams.append(key, value);
        } else {
            queryParams.set(key, value);
        }
    }
    
    // Aggiunge filtri preimpostati
    if (mapConfig.projectFilter && !queryParams.has('project')) {
        queryParams.set('project', mapConfig.projectFilter);
    }
    if (mapConfig.subprojectFilter && !queryParams.has('subproject')) {
        queryParams.set('subproject', mapConfig.subprojectFilter);
    }
    
    // Effettua la richiesta AJAX
    fetch(`${mapConfig.stationsApiUrl}?${queryParams.toString()}`)
        .then(response => response.json())
        .then(data => {
            // Aggiorna la sorgente delle stazioni
            stationsSource = data;
            map.getSource('stations').setData(data);
            
            // Aggiorna il conteggio delle stazioni visibili
            visibleStations = data.features;
            document.getElementById('visibleStationsCount').textContent = visibleStations.length;
            
            // Conserva gli ID delle stazioni per il salvataggio della mappa
            const stationIds = visibleStations.map(station => station.properties.id).join(',');
            document.getElementById('mapStationIds').value = stationIds;
        })
        .catch(error => console.error('Errore nel caricamento delle stazioni:', error));
}

/**
 * Carica i marker personalizzati dalla API
 */
function loadMarkers() {
    // Controlla se i marker devono essere mostrati
    const showMarkers = document.getElementById('showCustomMarkers').checked;
    
    if (!showMarkers) {
        markersSource = { type: 'FeatureCollection', features: [] };
        map.getSource('markers').setData(markersSource);
        return;
    }
    
    // Prepara i parametri della query
    let queryParams = new URLSearchParams();
    
    // Aggiunge filtri preimpostati
    if (mapConfig.projectFilter) {
        queryParams.set('project', mapConfig.projectFilter);
    }
    if (mapConfig.subprojectFilter) {
        queryParams.set('subproject', mapConfig.subprojectFilter);
    }
    
    // Effettua la richiesta AJAX
    fetch(`${mapConfig.markersApiUrl}?${queryParams.toString()}`)
        .then(response => response.json())
        .then(data => {
            // Aggiorna la sorgente dei marker
            markersSource = data;
            map.getSource('markers').setData(data);
            
            // Aggiorna il conteggio dei marker
            document.getElementById('customMarkersCount').textContent = data.features.length;
            
            // Conserva gli ID dei marker per il salvataggio della mappa
            const markerIds = data.features.map(marker => marker.properties.id).join(',');
            document.getElementById('mapMarkerIds').value = markerIds;
        })
        .catch(error => console.error('Errore nel caricamento dei marker:', error));
}

/**
 * Carica una mappa salvata
 * @param {number} mapId - ID della mappa salvata
 */
function loadSavedMap(mapId) {
    fetch(mapConfig.savedMapDataUrl)
        .then(response => response.json())
        .then(data => {
            // Imposta la posizione della mappa
            map.setCenter([data.center.lng, data.center.lat]);
            map.setZoom(data.zoom);
            
            // Imposta i filtri dal JSON salvato
            if (data.filters) {
                const form = document.getElementById('mapFilterForm');
                
                // Popola il form con i filtri salvati
                for (const [key, value] of Object.entries(data.filters)) {
                    const element = form.elements[key];
                    
                    if (element) {
                        if (element.type === 'checkbox') {
                            element.checked = value;
                        } else {
                            element.value = value;
                        }
                    }
                }
                
                // Applica i filtri
                applyFilters();
            }
        })
        .catch(error => console.error('Errore nel caricamento della mappa salvata:', error));
}

/**
 * Applica i filtri della mappa
 */
function applyFilters() {
    // Aggiorna le impostazioni di clustering
    const showClusters = document.getElementById('showClusters').checked;
    map.getSource('stations').setClusterProperty('cluster', showClusters);
    
    // Carica le stazioni con i nuovi filtri
    loadStations();
    
    // Carica i marker
    loadMarkers();
    
    // Salva i filtri applicati per il salvataggio della mappa
    saveCurrentFilters();
}

/**
 * Salva i filtri correnti in un campo nascosto
 */
function saveCurrentFilters() {
    const form = document.getElementById('mapFilterForm');
    const formData = new FormData(form);
    
    // Crea un oggetto con i valori dei filtri
    let filters = {};
    
    for (const [key, value] of formData.entries()) {
        // Gestisce i checkbox multipli
        if (key.endsWith('[]')) {
            const shortKey = key.slice(0, -2);
            
            if (!filters[shortKey]) {
                filters[shortKey] = [];
            }
            
            filters[shortKey].push(value);
        } else {
            // Gestisce input normali
            const element = form.elements[key];
            
            if (element.type === 'checkbox') {
                filters[key] = element.checked;
            } else {
                filters[key] = value;
            }
        }
    }
    
    // Salva i filtri come JSON
    document.getElementById('mapFiltersJson').value = JSON.stringify(filters);
}

/**
 * Reimposta i filtri ai valori predefiniti
 */
function resetFilters() {
    const form = document.getElementById('mapFilterForm');
    form.reset();
    
    // Riabilita tutti i checkbox di stato
    document.getElementById('statusPlanned').checked = true;
    document.getElementById('statusUnderConstruction').checked = true;
    document.getElementById('statusOperational').checked = true;
    document.getElementById('statusMaintenance').checked = false;
    document.getElementById('statusOffline').checked = false;
    
    // Riabilita visualizzazione cluster
    document.getElementById('showClusters').checked = true;
    
    // Riabilita marker personalizzati
    document.getElementById('showCustomMarkers').checked = true;
    
    // Applica i filtri
    applyFilters();
}

/**
 * Prepara i dati per il salvataggio della mappa
 */
function prepareMapSave() {
    // Ottiene le coordinate e lo zoom corrente
    const center = map.getCenter();
    document.getElementById('mapCenterLat').value = center.lat;
    document.getElementById('mapCenterLng').value = center.lng;
    document.getElementById('mapZoom').value = map.getZoom();
    
    // I filtri sono già stati salvati in applyFilters
    // Le stazioni sono già state salvate in loadStations
    // I marker sono già stati salvati in loadMarkers
    
    // Salva IDs dei progetti/sotto-progetti (non implementato)
    document.getElementById('mapProjectIds').value = '';
    document.getElementById('mapSubprojectIds').value = '';
}

/**
 * Attiva la modalità di aggiunta marker
 */
function enableAddMarkerMode() {
    // Mostra i controlli di disegno
    document.querySelector('.mapbox-gl-draw_point').style.display = 'block';
    document.querySelector('.mapbox-gl-draw_trash').style.display = 'block';
    
    // Attiva il tool di disegno per punto
    mapboxDraw.changeMode('draw_point');
    
    // Cambia cursore
    map.getCanvas().style.cursor = 'crosshair';
}

/**
 * Disattiva la modalità di aggiunta marker
 */
function disableAddMarkerMode() {
    // Nasconde i controlli di disegno
    document.querySelector('.mapbox-gl-draw_point').style.display = 'none';
    document.querySelector('.mapbox-gl-draw_trash').style.display = 'none';
    
    // Ripristina il cursore
    map.getCanvas().style.cursor = '';
    
    // Cancella tutti i punti disegnati
    mapboxDraw.deleteAll();
}

/**
 * Restituisce la classe CSS per il badge dello stato
 * @param {string} status - Stato della stazione
 * @returns {string} Classe CSS per il badge
 */
function getStatusBadgeClass(status) {
    switch(status) {
        case 'planned':
            return 'badge-primary';
        case 'under_construction':
            return 'badge-warning';
        case 'operational':
            return 'badge-success';
        case 'maintenance':
            return 'badge-light';
        case 'offline':
            return 'badge-danger';
        default:
            return 'badge-primary';
    }
}

/**
 * Inizializza i gestori degli eventi
 */
function initEventHandlers() {
    // Form filtri
    const filterForm = document.getElementById('mapFilterForm');
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        applyFilters();
    });
    
    // Bottone reset filtri
    const resetButton = document.getElementById('resetFiltersBtn');
    resetButton.addEventListener('click', resetFilters);
    
    // Bottone salva mappa
    const saveMapBtn = document.getElementById('saveMapBtn');
    saveMapBtn.addEventListener('click', function() {
        prepareMapSave();
        $('#saveMapModal').modal('show');
    });
    
    // Bottone aggiungi marker
    const addMarkerBtn = document.getElementById('addMarkerBtn');
    addMarkerBtn.addEventListener('click', function() {
        enableAddMarkerMode();
    });
    
    // Evento annulla modal salva mappa
    $('#saveMapModal').on('hidden.bs.modal', function() {
        // Reset del form
        document.getElementById('saveMapForm').reset();
    });
    
    // Checkbox cluster
    document.getElementById('showClusters').addEventListener('change', function() {
        // Aggiorna la sorgente cluster
        if (map.getSource('stations')) {
            map.getSource('stations').setClusterProperty('cluster', this.checked);
        }
    });
    
    // Checkbox marker personalizzati
    document.getElementById('showCustomMarkers').addEventListener('change', function() {
        loadMarkers();
    });
}