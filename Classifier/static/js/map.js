// js/map.js

/**
 * Layflet map init
 * @returns {{map: L.Map, drawnItems: L.FeatureGroup}}
 */
export function initMap() {
  const map = L.map('map', {
    center: [51.9194, 19.1451],
    zoom: 8, // 8 lepiej dla 55/45 splitu
    minZoom: 6,
    maxZoom: 13,
    zoomSnap: 1,
    zoomDelta: 1,
    wheelPxPerZoomLevel: 120,
    maxBoundsViscosity: 1.0
  });

  map.createPane('labels');
  map.getPane('labels').style.zIndex = 650;
  map.getPane('labels').style.pointerEvents = 'none';

  const satelliteLayer = L.tileLayer('/tiles/{z}/{x}/{y}.jpg', {
    maxZoom: 13,
    tms: true,
    noWrap: true,
    bounds: [[49, 14], [55, 25]],
    attribution: '© Satellite'
  }).addTo(map);

  const labelOverlay = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_only_labels/{z}/{x}/{y}.png', {
    attribution: '© CartoDB, © OpenStreetMap contributors',
    opacity: 0.8,
    pane: 'labels',
  }).addTo(map);

  addPolandBorders(map);

  const drawnItems = new L.FeatureGroup();
  map.addLayer(drawnItems);

  const drawControl = new L.Control.Draw({
    draw: {
      rectangle: true,
      polygon: false,
      marker: false,
      circle: false,
      polyline: false
    },
    edit: {
      featureGroup: drawnItems
    }
  });
  map.addControl(drawControl);

  const baseLayers = { "Powierzchnia satelitarna": satelliteLayer };
  const overlays = { "Miasta": labelOverlay };
  L.control.layers(baseLayers, overlays).addTo(map);

  return { map, drawnItems };
}

/**
 * @param {L.Map} map
 */
async function addPolandBorders(map) {
  try {
    const [countryResp, wojResp] = await Promise.all([
      fetch('/static/geodata/poland.country.json'),
      fetch('/static/geodata/wojewodztwa-max.geojson')
    ]);

    const polandGeoJson = await countryResp.json();
    const wojewodztwaGeoJson = await wojResp.json();
    // const powiatyGeo = await wojResp.json();

    // Country outline
    L.geoJSON(polandGeoJson, {
      style: feature => ({
        color: 'white',
        weight: 3,
        opacity: 0.8,
        fillOpacity: 0
      })
    }).addTo(map);

    const wojLayer = L.geoJSON(wojewodztwaGeoJson, {
      style: feature => ({
        color: 'white',
        weight: 1.2,
        opacity: 0.4,
        fillOpacity: 0
      }),
      onEachFeature: (feature, layer) => {
        const name =
          feature.properties?.nazwa ||
          feature.properties?.NAME_1 ||
          feature.properties?.NAME ||
          'Nieznany';
        layer.bindTooltip(name, {
          permanent: false,
          direction: 'center',
          className: 'region-label'
        });
      }
    }).addTo(map);

    wojLayer.bringToFront();
  } catch (err) {
    console.error('Failed to load GeoJSON layers:', err);
  }
}