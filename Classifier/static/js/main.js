import { initMap } from './map.js';
import { runAnalysis } from './analysis.js';
import { resetStatsUI, setupModalControls, showParamModal, initializeSplitter } from './ui.js';

// land area irt global state+
let lastRectBounds = null;

document.addEventListener('DOMContentLoaded', () => {
    // INIT PART
    const { map, drawnItems } = initMap();
    resetStatsUI(); // Ensure initial UI state is clean

    initializeSplitter(map);
    // Helper to clear the drawn rectangle
    const clearDrawnItems = () => {
        drawnItems.clearLayers();
        lastRectBounds = null;
    };

    // UI EVENT
    setupModalControls(clearDrawnItems);

    // DRAW
    map.on(L.Draw.Event.CREATED, e => {
      drawnItems.clearLayers();
      resetStatsUI();
      const layer = e.layer;
      drawnItems.addLayer(layer);
      lastRectBounds = layer.getBounds();
      showParamModal();
    });

    // ~~ĄNALYSIS FORM TODO TRANSFER TO UI?
    document.getElementById('paramForm').onsubmit = async (e) => {
        e.preventDefault();
        if (!lastRectBounds) return;
        const preview = document.getElementById('preview');
        const statsBars = document.getElementById('statsBars');
        const downloadJsonBtn = document.getElementById('downloadJsonBtn');

        preview.style.display = 'none';
        statsBars.innerHTML = '<div style="text-align:center; padding: 20px;">Processing...</div>';
        downloadJsonBtn.style.display = 'none';
        // preview.style.display = 'none';
        // statsBars.innerHTML = '<div style="text-align:center; padding: 4px;">INPUT IMAGE</div>';
        // downloadJsonBtn.style.display = 'none';

        await runAnalysis(lastRectBounds, map.getZoom());
    };
});