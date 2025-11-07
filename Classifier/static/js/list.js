document.addEventListener("DOMContentLoaded", function() {
  let selectedWoj = null;
  let geojsonLayer = null;

  const configModal = document.getElementById('configModal');
  const modalTitle = document.getElementById('modalTitle');
  const map = L.map('map', {
    center: [51.9194, 19.1451],
    zoom: 7,
    minZoom: 6,
    maxZoom: 13,
    zoomSnap: 1,
    zoomDelta: 1
  });

  L.tileLayer('/tiles/{z}/{x}/{y}.jpg', {
    maxZoom: 13,
    tms: true,
    noWrap: true,
    bounds: [[49, 14], [55, 25]],
    attribution: '© Satellite'
  }).addTo(map);

  async function addPolandBorders() {
    try {
      const [countryResp, wojResp] = await Promise.all([
        fetch('/static/geodata/poland.country.json'),
        fetch('/static/geodata/wojewodztwa-max.geojson')
      ]);

      const polandGeoJson = await countryResp.json();
      const wojewodztwaGeoJson = await wojResp.json();

      L.geoJSON(polandGeoJson, {
        style: {
          color: 'white',
          weight: 3,
          opacity: 0.8,
          fillOpacity: 0
        }
      }).addTo(map);

      geojsonLayer = L.geoJSON(wojewodztwaGeoJson, {
        style: function(feature) {
          return {
            fillColor: '#7f8c8d',
            fillOpacity: 0.0,
            color: 'white',
            weight: 1.2,
            opacity: 0.4
          };
        },
        onEachFeature: function(feature, layer) {
          const name = feature.properties?.nazwa ||
                      feature.properties?.NAME_1 ||
                      feature.properties?.NAME ||
                      'Nieznany';

          layer.on({
            click: function(e) {
              selectWojewodztwo(feature.properties.id);
            },
            mouseover: function(e) {
              if (!selectedWoj || selectedWoj.id !== feature.properties.id) {
                e.target.setStyle({ fillOpacity: 0.7 });
              }
            },
            mouseout: function(e) {
              if (!selectedWoj || selectedWoj.id !== feature.properties.id) {
                e.target.setStyle({ fillOpacity: 0.0 });
              }
            }
          });

          layer.bindTooltip(name, {
            permanent: false,
            direction: 'center',
            className: 'region-label'
          });
        }
      }).addTo(map);

      geojsonLayer.bringToFront();
    } catch (err) {
      console.error('Failed to load GeoJSON layers:', err);
    }
  }

  addPolandBorders();

  // Handle wojewodztwo item clicks
  document.querySelectorAll('.wojewodztwo-item').forEach(item => {
    item.addEventListener('click', function() {
      const id = parseInt(this.dataset.id);
      selectWojewodztwo(id);
    });
  });

  function selectWojewodztwo(id) {
    const item = document.querySelector(`.wojewodztwo-item[data-id="${id}"]`);
    if (!item) return;

    const nazwa = item.dataset.nazwa;
    const bounds = JSON.parse(item.dataset.bounds);
    const analyzed = item.classList.contains('analyzed');

    selectedWoj = { id, nazwa, bounds, analyzed };

    document.querySelectorAll('.wojewodztwo-item').forEach(el => {
      el.classList.remove('selected');
    });
    item.classList.add('selected');
    if (geojsonLayer) {
      geojsonLayer.eachLayer(layer => {
        if (layer.feature.properties.id === id) {
          layer.setStyle({
            fillColor: '#3498db',
            fillOpacity: 0.4,
            color: '#3498db',
            weight: 3
          });
          map.fitBounds(layer.getBounds(), { padding: [50, 50] });
        } else {
          layer.setStyle({
            fillColor: '#7f8c8d',
            fillOpacity: 0.2,
            color: 'white',
            weight: 1.2
          });
        }
      });
    }

    modalTitle.textContent = `Configure Analysis: ${nazwa.charAt(0).toUpperCase() + nazwa.slice(1)}`;

    // todo ui button dla okna
    if (analyzed) {
      if (confirm(`${nazwa} Juz bylo przeanalizowane. Chcesz zobaczyc strone?`)) {
        window.location.href = `/wojewodztwo/${id}/`;
      } else {
        configModal.showModal();
      }
    } else {
      configModal.showModal();
    }
  }

  document.getElementById('cancelBtn').onclick = () => {
    configModal.close();
  };

  document.getElementById('runAnalyzeBtn').onclick = () => {
    if (!selectedWoj) return;

    configModal.close();
    runAnalysis(selectedWoj.id);
  };

  function runAnalysis(wojewodztwoId) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';

    const modelPath = document.getElementById('modelSelect').value;
    const tileSize = parseInt(document.getElementById('tileSize').value);
    const zoomLevel = parseInt(document.getElementById('zoomLevel').value);
    const applySmoothing = document.getElementById('applySmoothing').checked;

    fetch('/api/analyze-wojewodztwo/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        wojewodztwo_id: wojewodztwoId,
        model_path: modelPath,
        params: {
          TILE_SIZE: tileSize,
          APPLY_SMOOTHING: applySmoothing
        },
        zoom: zoomLevel,
        force_recompute: false
      })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success || data.cached) {
        window.location.href = data.redirect_url;
      } else {
        alert('Analysis failed: ' + (data.error || 'Unknown error'));
        overlay.style.display = 'none';
      }
    })
    .catch(err => {
      console.error('Analysis error:', err);
      alert('Analysis failed: ' + err.message);
      overlay.style.display = 'none';
    });
  }
});