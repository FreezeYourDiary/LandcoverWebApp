import { setProgress, displayResults } from './ui.js';
/**
 * + backend requset analysis
 * @param {L.LatLngBounds} rectBounds - bbox
 * @param {number} zoom - zoom
 * @returns {Promise<boolean>} - return success
 */
export async function runAnalysis(rectBounds, zoom) {
  console.log('[DEBUG] Frontend start');
  console.log('[DEBUG] bbox:', rectBounds);
  console.log('[DEBUG] zoom:', zoom);

  const paramForm = document.getElementById('paramForm');
  const paramModal = document.getElementById('paramModal');

  // + unified params
  const modelPath = document.getElementById('modelSelect')?.value;
  const analysisMode = document.getElementById('analysisMode')?.value;
  const applySmoothing = document.getElementById('smoothing')?.checked;
  const applyInterpolation = document.getElementById('interpolation')?.checked;  // NEW
  const useSimplified = document.getElementById('simplifiedClasses')?.checked;  // NEW
  const fixSeaLake = document.getElementById('fixSeaLake')?.checked;

  console.log('[DEBUG] Params:', {
    modelPath, analysisMode, applySmoothing,
    applyInterpolation, useSimplified, fixSeaLake
  });

  const bbox = [
    rectBounds.getSouthWest().lng,
    rectBounds.getSouthWest().lat,
    rectBounds.getNorthEast().lng,
    rectBounds.getNorthEast().lat
  ];

  console.log('[DEBUG] BBox:', bbox);

  const payload = {
    bbox,
    zoom: zoom,
    model_path: modelPath,
    params: {
      ANALYSIS_MODE: analysisMode,
      APPLY_SMOOTHING: applySmoothing,
      APPLY_INTERPOLATION: applyInterpolation,
      USE_SIMPLIFIED_CLASSES: useSimplified,
      FIX_SEALAKE: fixSeaLake
    }
  };

  console.log('[DEBUG] Payload:', JSON.stringify(payload, null, 2));

  paramModal.close();
  setProgress(0);

  try {
    setProgress(1);
    console.log('[DEBUG] to api /analyze-bbox/');

    const resp = await fetch('/analyze-bbox/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    console.log('[DEBUG] respstatus:', resp.status);

    if (!resp.ok) {
      throw new Error(`HTTP error! status: ${resp.status}`);
    }

    const j = await resp.json();
    console.log('[DEBUG] response: ', j);

    if (j.error) {
      console.error('[ERROR] Server error:', j.error);
      document.getElementById('statsBars').textContent = "Error: " + j.error;
      setProgress(0);
      return false;
    }

    setProgress(3);
    console.log('[DEBUG] Displaying results...');
    displayResults(j);
    console.log('[DEBUG] analysis done');
    return true;

  } catch (err) {
    console.error('Analysis err:', err);
    console.error('Stack err:', err.stack);
    document.getElementById('statsBars').textContent = "Request failed: " + err.message;
    setProgress(0);
    return false;
  }
}