import { initMap } from './map.js';
import { runAnalysis } from './analysis.js';
import { resetStatsUI, setupModalControls, showParamModal, initializeSplitter } from './ui.js';

let lastRectBounds = null;

document.addEventListener('DOMContentLoaded', () => {
    const { map, drawnItems } = initMap();
    resetStatsUI();
    initializeSplitter(map);

    const clearDrawnItems = () => {
        drawnItems.clearLayers();
        lastRectBounds = null;
    };

    setupModalControls(clearDrawnItems);

     map.on(L.Draw.Event.CREATED, e => {
        const layer = e.layer;
        const bounds = layer.getBounds();

        const latDiff = bounds.getNorth() - bounds.getSouth();
        const lngDiff = bounds.getEast() - bounds.getWest();

        // 1 degree lat =~ 111 km
        // 1 degree long =~ 111 * cos(lat) km
        const centerLat = (bounds.getNorth() + bounds.getSouth()) / 2;
        const heightKm = latDiff * 111;
        const widthKm = lngDiff * 111 * Math.cos(centerLat * Math.PI / 180);

        const MIN_WIDTH_KM = 0.5;
        const MIN_HEIGHT_KM = 0.5;
        const MIN_AREA_KM2 = 0.25;  // km2

        const areaKm2 = heightKm * widthKm;

        console.log(`[DEBUG] Box dimensions: ${widthKm.toFixed(2)}km x ${heightKm.toFixed(2)}km = ${areaKm2.toFixed(2)}km²`);

        if (widthKm < MIN_WIDTH_KM || heightKm < MIN_HEIGHT_KM || areaKm2 < MIN_AREA_KM2) {
            alert(
                `Wybrany obszar jest za mały!\n\n` +
                `Wymiary: ${widthKm.toFixed(2)}km × ${heightKm.toFixed(2)}km (${areaKm2.toFixed(2)}km²)\n` +
                `Minimum: ${MIN_WIDTH_KM}km × ${MIN_HEIGHT_KM}km (${MIN_AREA_KM2}km²)\n\n` +
                `Proszę narysować większy prostokąt.`
            );
            return;
        }

        const MAX_WIDTH_KM = 50;
        const MAX_HEIGHT_KM = 50;
        const MAX_AREA_KM2 = 500;

        if (widthKm > MAX_WIDTH_KM || heightKm > MAX_HEIGHT_KM || areaKm2 > MAX_AREA_KM2) {
            alert(
                `Wybrany obszar jest za duży!\n\n` +
                `Wymiary: ${widthKm.toFixed(2)}km × ${heightKm.toFixed(2)}km (${areaKm2.toFixed(2)}km²)\n` +
                `Maximum: ${MAX_WIDTH_KM}km × ${MAX_HEIGHT_KM}km (${MAX_AREA_KM2}km²)\n\n` +
                `Proszę narysować mniejszy prostokąt.`
            );
            return; // Don't add the layer
        }

        drawnItems.clearLayers();
        resetStatsUI();
        drawnItems.addLayer(layer);
        lastRectBounds = bounds;
        showParamModal();
    });

    const paramForm = document.getElementById('paramForm');
    const runAnalyzeBtn = document.getElementById('runAnalyzeBtn');
    // prevent page refresh https://gonzaleznyc.medium.com/when-e-preventdefault-isnt-working-and-other-sleepless-nights-fa57a40c7e0f
    if (paramForm) {
        paramForm.onsubmit = (e) => {
            e.preventDefault();
            return false;
        };
    }

    if (runAnalyzeBtn) {
        runAnalyzeBtn.onclick = async (e) => {
            e.preventDefault();
            if (!lastRectBounds) {
                alert('Najpierw narysuj obszar na mapie');
                return;
            }

            const statsBars = document.getElementById('statsBars');
            statsBars.innerHTML = '<div style="text-align:center; padding: 20px;">Analiza w toku...</div>';

            try {
                await runAnalysis(lastRectBounds, map.getZoom());
            } catch (error) {
                console.error('Analysis error:', error);
                statsBars.innerHTML = `<div style="color: red;">Error: ${error.message}</div>`;
            }
        };
    }
});