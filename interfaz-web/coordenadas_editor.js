/**
 * Editor de Coordenadas - Permite seleccionar coordenadas desde el mapa
 * Haz clic en el mapa para obtener coordenadas exactas
 */

let editorMode = false;
let coordenadasSeleccionadas = {};
let markerEditor = null;

// Agregar funcionalidad al cargar la página
document.addEventListener('DOMContentLoaded', () => {
    // Crear botón para activar el modo editor
    crearBotonEditor();
});

function crearBotonEditor() {
    // Esperar a que el mapa esté listo
    const intervalo = setInterval(() => {
        if (estado && estado.mapa) {
            clearInterval(intervalo);
            
            // Crear contenedor para el modo editor
            const editorContainer = document.createElement('div');
            editorContainer.id = 'editor-coordenadas-container';
            editorContainer.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: white;
                border: 2px solid #3b82f6;
                border-radius: 10px;
                padding: 15px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.15);
                z-index: 1000;
                font-family: Arial, sans-serif;
                max-width: 350px;
            `;
            
            editorContainer.innerHTML = `
                <div style="margin-bottom: 10px;">
                    <button id="btn-modo-editor" style="
                        width: 100%;
                        padding: 10px;
                        background: #3b82f6;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        cursor: pointer;
                        font-weight: bold;
                        font-size: 14px;
                    ">
                        🗺️ MODO SELECCIONAR COORDENADAS
                    </button>
                </div>
                <div id="editor-info" style="
                    display: none;
                    background: #f0f4f8;
                    padding: 12px;
                    border-radius: 5px;
                    font-size: 12px;
                ">
                    <p style="margin: 0 0 8px 0; color: #666;">
                        ✓ Modo ACTIVADO - Haz clic en el mapa
                    </p>
                    <div style="
                        background: white;
                        padding: 10px;
                        border-radius: 4px;
                        margin-bottom: 8px;
                        border: 1px solid #d1d5db;
                    ">
                        <p style="margin: 0; font-size: 11px; color: #333;">
                            <strong>Latitud:</strong> <span id="editor-lat">-12.0000</span>
                        </p>
                        <p style="margin: 5px 0 0 0; font-size: 11px; color: #333;">
                            <strong>Longitud:</strong> <span id="editor-lng">-77.0000</span>
                        </p>
                    </div>
                    <button id="btn-copiar-coords" style="
                        width: 100%;
                        padding: 8px;
                        background: #10b981;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                        margin-bottom: 8px;
                    ">
                        📋 Copiar Coordenadas
                    </button>
                    <button id="btn-salir-editor" style="
                        width: 100%;
                        padding: 8px;
                        background: #ef4444;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                    ">
                        ✕ Salir del Modo
                    </button>
                </div>
            `;
            
            document.body.appendChild(editorContainer);
            
            // Event listeners
            document.getElementById('btn-modo-editor').addEventListener('click', toggleEditorMode);
            document.getElementById('btn-salir-editor').addEventListener('click', toggleEditorMode);
            document.getElementById('btn-copiar-coords').addEventListener('click', copiarCoordenas);
            
            // Agregar indicador visual en el mapa
            agregarControlesAlMapa();
        }
    }, 500);
}

function toggleEditorMode() {
    editorMode = !editorMode;
    const btnModo = document.getElementById('btn-modo-editor');
    const infoDiv = document.getElementById('editor-info');
    
    if (editorMode) {
        btnModo.style.background = '#ef4444';
        btnModo.textContent = '🗺️ MODO ACTIVO - Haz clic en el mapa';
        infoDiv.style.display = 'block';
        
        // Cambiar cursor del mapa
        estado.mapa._container.style.cursor = 'crosshair';
        
        // Agregar event listener de click al mapa
        estado.mapa.on('click', function(e) {
            if (editorMode) {
                const lat = e.latlng.lat;
                const lng = e.latlng.lng;
                
                // Actualizar información
                document.getElementById('editor-lat').textContent = lat.toFixed(4);
                document.getElementById('editor-lng').textContent = lng.toFixed(4);
                
                // Guardar coordenadas
                coordenadasSeleccionadas = { lat, lng };
                
                // Agregar marcador en el mapa
                if (markerEditor) {
                    estado.mapa.removeLayer(markerEditor);
                }
                
                markerEditor = L.marker([lat, lng], {
                    icon: L.icon({
                        iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIzMiIgaGVpZ2h0PSIzMiIgdmlld0JveD0iMCAwIDMyIDMyIj48Y2lyY2xlIGN4PSIxNiIgY3k9IjEyIiByPSI5IiBmaWxsPSIjZWY0NDQ0Ii8+PGNpcmNsZSBjeD0iMTYiIGN5PSIxMiIgcj0iNiIgZmlsbD0id2hpdGUiLz48L3N2Zz4=',
                        iconSize: [32, 32],
                        iconAnchor: [16, 16]
                    })
                }).addTo(estado.mapa);
                
                // Mostrar popup con coordenadas
                markerEditor.bindPopup(`
                    <div style="text-align: center; font-family: monospace;">
                        <strong>Coordenadas Seleccionadas</strong><br>
                        Latitud: ${lat.toFixed(4)}<br>
                        Longitud: ${lng.toFixed(4)}
                    </div>
                `).openPopup();
            }
        });
        
        // Mensaje en consola
        console.log('%c✓ MODO EDITOR ACTIVADO', 'color: #10b981; font-size: 14px; font-weight: bold;');
        console.log('Haz clic en el mapa para seleccionar coordenadas. Luego copia los valores con el botón "Copiar Coordenadas"');
    } else {
        btnModo.style.background = '#3b82f6';
        btnModo.textContent = '🗺️ MODO SELECCIONAR COORDENADAS';
        infoDiv.style.display = 'none';
        estado.mapa._container.style.cursor = 'grab';
        
        // Remover el event listener de click
        estado.mapa.off('click');
        
        // Remover marcador
        if (markerEditor) {
            estado.mapa.removeLayer(markerEditor);
            markerEditor = null;
        }
        
        console.log('%c✓ Modo editor desactivado', 'color: #666; font-size: 12px;');
    }
}

function copiarCoordenas() {
    if (coordenadasSeleccionadas.lat && coordenadasSeleccionadas.lng) {
        const texto = `latitud: ${coordenadasSeleccionadas.lat.toFixed(4)},\nlongitud: ${coordenadasSeleccionadas.lng.toFixed(4)},`;
        
        navigator.clipboard.writeText(texto).then(() => {
            alert('✓ Coordenadas copiadas al portapapeles:\n\n' + texto);
        }).catch(() => {
            alert('Error al copiar. Copia manualmente:\n' + texto);
        });
    } else {
        alert('Primero selecciona un punto en el mapa');
    }
}

function agregarControlesAlMapa() {
    // Crear un control personalizado para mostrar coordenadas
    const CoordControl = L.Control.extend({
        options: {
            position: 'topleft'
        },
        onAdd: function(map) {
            const div = L.DomUtil.create('div', 'leaflet-control-zoom leaflet-bar');
            div.innerHTML = `
                <a title="Información de Coordenadas" style="
                    width: 36px;
                    height: 36px;
                    line-height: 36px;
                    text-align: center;
                    cursor: default;
                    background: white;
                    border-radius: 4px;
                    font-weight: bold;
                    color: #3b82f6;
                ">
                    🎯
                </a>
            `;
            return div;
        }
    });
    
    if (estado.mapa) {
        new CoordControl().addTo(estado.mapa);
    }
}

console.log('%c📍 Editor de Coordenadas cargado', 'color: #3b82f6; font-size: 12px;');
console.log('Usa el botón "MODO SELECCIONAR COORDENADAS" en la esquina inferior derecha');
