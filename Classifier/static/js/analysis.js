import { setProgress, displayResults } from './ui.js';
/**
 * + backend requset analysis
 * @param {L.LatLngBounds} rectBounds - bbox
 * @param {number} zoom - zoom
 * @returns {Promise<boolean>} - return success
 */
export async function runAnalysis(rectBounds, zoom) {
  const paramForm = document.getElementById('paramForm');
  const paramModal = document.getElementById('paramModal'); // DOMLOADER for access

  const params = {
    TILE_SIZE: parseInt(paramForm.elements['tile_size'].value, 10),
    IMG_SIZE: parseInt(paramForm.elements['img_size'].value, 10),
    APPLY_SMOOTHING: paramForm.elements['smoothing'].checked
  };

  const bbox = [
    rectBounds.getSouthWest().lng,
    rectBounds.getSouthWest().lat,
    rectBounds.getNorthEast().lng,
    rectBounds.getNorthEast().lat
  ];
/** TODO fix config for model_path*/
  const payload = {
    bbox,
    zoom: zoom,
    params,

    model_path: "Classifier/inputs/networks/mobilenetv2_v3.keras"
  };

  paramModal.close();
  // in UI.js
  setProgress(0);

  try {
      // TODO actuall progress
    setProgress(1);
    await new Promise(r => setTimeout(r, 500));
    setProgress(2);
    await new Promise(r => setTimeout(r, 500));
    setProgress(3);

    const resp = await fetch('/analyze-bbox/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const j = await resp.json();
    if (j.error) {
      document.getElementById('statsBars').textContent = "Error: " + j.error;
      setProgress(0);
      return false;
    }

    displayResults(j);
    return true;

  } catch (err) {
    document.getElementById('statsBars').textContent = "Request failed: " + err.message;
    console.error(err);
    setProgress(0);
    return false;
  }
}