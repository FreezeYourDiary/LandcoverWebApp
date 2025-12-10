const paramModal = document.getElementById('paramModal');
const statsBars = document.getElementById('statsBars');
const progressPanel = document.getElementById('progressPanel');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');
const viewRawJsonBtn = document.getElementById('viewRawJsonBtn');
const imagesCard = document.getElementById('imagesCard');
let currentStats = null;
let currentImages = null;

function getClassColor(className) {
  return window.AppConfig?.classColors?.[className] || "#999";
}

function getClassNamePL(className) {
  return window.AppConfig?.classNamesPL?.[className] || className;
}

export function resetStatsUI() {
  const tabsHeader = document.getElementById('tabsHeader');
  if (tabsHeader) tabsHeader.innerHTML = "";
  statsBars.innerHTML = "Analiza rozpocznie się po wybraniu strefy, którą chcesz przeanalizować na mapie.";
  downloadJsonBtn.style.display = 'none';
  viewRawJsonBtn.style.display = 'none';
  if (imagesCard) imagesCard.style.display = 'none';
  currentStats = null;
  currentImages = null;
}

export function setProgress(index) {
  const steps = progressPanel.querySelectorAll('.progress-step');
  steps.forEach((el, i) => {
    el.classList.remove('done', 'active', 'pending');
    if (i < index) el.classList.add('done');
    else if (i === index) el.classList.add('active');
    else el.classList.add('pending');
  });
}

export function displayResults({ stats, tabs, preview_image, original_image, mask_image, residential_image }) {
  console.log('[DEBUG ui.js] displayResults called');
  console.log('[DEBUG] residential_image:', residential_image ? 'EXISTS' : 'NULL');

  currentStats = stats;
  currentImages = {
    original: original_image,
    mask: mask_image,
    preview: preview_image,
    residential: residential_image
  };

  downloadJsonBtn.style.display = 'inline-block';
  viewRawJsonBtn.style.display = 'inline-block';

  if (tabs && tabs.length > 0) {
    console.log('[DEBUG] Creating tabs:', tabs);
    createTabs(tabs);
  } else {
    console.log('[DEBUG] Default bars');
    drawStatsBars({ areas_pct: stats.areas_pct || {} });
  }

  if (original_image || mask_image || preview_image || residential_image) {
    displayImages({
      original: original_image,
      mask: mask_image,
      blended: preview_image,
      residential: residential_image
    });
  } else {
    console.log('[DEBUG] No images');
  }
}

function displayImages(images) {
  if (!imagesCard) return;
  imagesCard.style.display = 'block';

  const originalImg = document.getElementById('originalImage');
  const maskImg = document.getElementById('maskImage');
  const blendedImg = document.getElementById('blendedImage');
  const residentialImg = document.getElementById('residentialImage');
  const residentialBtn = document.getElementById('residentialBtn');
  const downloadActiveBtn = document.getElementById('downloadActiveBtn');

  if (images.original && originalImg) {
    originalImg.src = images.original;
    setupImageZoom(originalImg);
  }
  if (images.mask && maskImg) {
    maskImg.src = images.mask;
    setupImageZoom(maskImg);
  }
  if (images.blended && blendedImg) {
    blendedImg.src = images.blended;
    setupImageZoom(blendedImg);
  }

  // NEW: Handle residential image
  if (images.residential && residentialImg && residentialBtn) {
    residentialImg.src = images.residential;
    residentialBtn.style.display = 'inline-block';
    setupImageZoom(residentialImg);
    console.log('[DEBUG] Residential image loaded and button shown');
  } else if (residentialBtn) {
    residentialBtn.style.display = 'none';
    console.log('[DEBUG] No residential image, button hidden');
  }

  if (downloadActiveBtn && (images.original || images.mask || images.blended || images.residential)) {
    downloadActiveBtn.style.display = 'block';
  }

  function getActiveView() {
    const activeBtn = document.querySelector('#imagesCard .image-control-btn.active[data-view]');
    return activeBtn ? activeBtn.dataset.view : 'original';
  }

  if (downloadActiveBtn) {
    downloadActiveBtn.onclick = () => {
      const view = getActiveView();
      let dataUrl = null;
      let filename = '';

      if (view === 'original' && images.original) {
        dataUrl = images.original;
        filename = 'original.jpg';
      } else if (view === 'mask' && images.mask) {
        dataUrl = images.mask;
        filename = 'mask.png';
      } else if (view === 'blended' && images.blended) {
        dataUrl = images.blended;
        filename = 'overlay.png';
      } else if (view === 'residential' && images.residential) {
        dataUrl = images.residential;
        filename = 'residential.png';
      }

      if (dataUrl) downloadImage(dataUrl, filename);
    };
  }

  // Switch views
  document.querySelectorAll('#imagesCard .image-control-btn[data-view]').forEach(btn => {
    btn.addEventListener('click', function() {
      const view = this.dataset.view;
      console.log('[DEBUG] Switching to view:', view);

      document.querySelectorAll('#imagesCard .image-control-btn[data-view]').forEach(b => b.classList.remove('active'));
      this.classList.add('active');

      document.querySelectorAll('.image-layer').forEach(layer => {
        layer.classList.remove('active');
        layer.style.opacity = '0';
      });

      const targetLayer = document.querySelector(`[data-layer="${view}"]`);
      if (targetLayer) {
        targetLayer.classList.add('active');
        targetLayer.style.opacity = '1';
      }
    });
  });
}

function setupImageZoom(img) {
  let zoomed = false;

  img.addEventListener('click', function() {
    if (!zoomed) {
      this.style.maxWidth = 'none';
      this.style.maxHeight = 'none';
      this.style.cursor = 'zoom-out';
      this.parentElement.style.overflow = 'auto';
      zoomed = true;
    } else {
      this.style.maxWidth = '100%';
      this.style.maxHeight = '100%';
      this.style.cursor = 'zoom-in';
      this.parentElement.style.overflow = 'hidden';
      zoomed = false;
    }
  });
}

function downloadImage(base64Data, filename) {
  const link = document.createElement('a');
  link.href = base64Data;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function viewRawStats() {
  if (!currentStats) return;
  const win = window.open('', '_blank');
  win.document.write('<pre>' + JSON.stringify(currentStats, null, 2) + '</pre>');
}

export function downloadStats() {
  if (!currentStats) return;
  const blob = new Blob([JSON.stringify(currentStats, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'landcover_stats.json';
  a.click();
  URL.revokeObjectURL(url);
}

function createTabs(tabs) {
  const tabsHeader = document.getElementById('tabsHeader');
  tabsHeader.innerHTML = "";

  let currentTab = tabs[0].key;

  tabs.forEach((tab, i) => {
    const btn = document.createElement('button');
    btn.className = 'image-control-btn btn-small';
    if (i === 0) btn.classList.add('active');
    btn.textContent = tab.label;
    btn.addEventListener('click', () => {
      currentTab = tab.key;
      document.querySelectorAll('#tabsHeader .image-control-btn').forEach(b => {
        b.classList.remove('active');
      });
      btn.classList.add('active');
      showTabContent(tab);
    });
    tabsHeader.appendChild(btn);
  });

  if (tabs.length > 0) showTabContent(tabs[0]);
}

function showTabContent(tab) {
  const container = document.getElementById('statsBars');
  container.innerHTML = "";

  console.log('[DEBUG] Showing tab:', tab.key, 'data:', tab.data);

  if (tab.key === 'density') {
    const value = tab.data || 0;
    const percentage = (value * 100).toFixed(2);
    container.innerHTML = `
      <div style="padding: 2rem; text-align: center;">
        <div style="font-size: 3rem; font-weight: 700; color: var(--accent-default); margin-bottom: 1rem;">
          ${percentage}%
        </div>
        <div style="color: var(--text-light); margin-bottom: 1rem;">Gęstość zabudowy</div>
        <div style="margin-top: 2rem; text-align: left; padding: 1rem; background: var(--bg-light); border-radius: 4px;">
          <strong>Interpretacja:</strong><br>
          ${percentage < 5 ? 'Obszar o bardzo niskiej zabudowie' : 
            percentage < 15 ? 'Obszar o niskiej zabudowie' :
            percentage < 30 ? 'Obszar o średniej zabudowie' :
            percentage < 50 ? 'Obszar o wysokiej zabudowie' :
            'Obszar silnie zurbanizowany'}
        </div>
      </div>
    `;
    return;
  }

  if (tab.key === 'adjacency') {
    renderAdjacencyMatrix(tab.data, container);
    return;
  }

  if (tab.key === 'percentage') {
    drawStatsBars({ areas_pct: tab.data });
    return;
  }

  if (tab.key === 'area') {
    drawTopAreas(tab.data);
    return;
  }

  if (tab.key === 'fragmentation') {
    drawFragmentation(tab.data);
    return;
  }

  const table = document.createElement('table');
  table.className = "simple-table";
  for (const [k, v] of Object.entries(tab.data || {})) {
    const row = document.createElement('tr');
    const val = typeof v === 'number' ? v.toFixed(3) : v;
    const namePL = getClassNamePL(k);
    row.innerHTML = `<td>${namePL}</td><td style="text-align:right;">${val}</td>`;
    table.appendChild(row);
  }
  container.appendChild(table);
}

function renderAdjacencyMatrix(data, container) {
  if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
    container.innerHTML = '<p style="text-align:center;color:var(--text-light);padding:2rem;">Brak danych macierzy sąsiedztwa</p>';
    return;
  }

  const classes = Object.keys(data);
  let html = '<div style="overflow-x: auto; padding: 1rem;"><table class="simple-table" style="border-collapse: collapse;"><tr><th style="padding: 8px; border: 1px solid var(--border-color); background: var(--bg-light);"></th>';

  classes.forEach(c => {
    const namePL = getClassNamePL(c);
    html += `<th style="padding: 8px; border: 1px solid var(--border-color); background: var(--bg-light); font-size: 0.75rem;">${namePL}</th>`;
  });
  html += '</tr>';

  classes.forEach(class1 => {
    const name1PL = getClassNamePL(class1);
    html += `<tr><th style="padding: 8px; border: 1px solid var(--border-color); background: var(--bg-light); text-align: left; font-size: 0.75rem;">${name1PL}</th>`;
    classes.forEach(class2 => {
      const value = data[class1]?.[class2] || 0;
      const percentage = (value * 100).toFixed(2);
      const intensity = Math.min(value / 0.2, 1);
      const bgColor = class1 === class2 ? 'var(--bg-light)' : `rgba(255, 12, 80, ${intensity * 0.7})`;
      const textColor = intensity > 0.5 && class1 !== class2 ? 'white' : 'var(--text-default)';
      html += `<td style="background: ${bgColor}; padding: 8px; border: 1px solid var(--border-color); color: ${textColor}; text-align: center; font-size: 0.75rem;">${class1 === class2 ? '-' : percentage}</td>`;
    });
    html += '</tr>';
  });

  html += '</table></div>';
  container.innerHTML = html;
}

function drawFragmentation(data) {
  const container = document.getElementById('statsBars');

  if (!data || Object.keys(data).length === 0) {
    container.innerHTML = '<div style="color: var(--text-light); padding: 1rem;">Brak danych</div>';
    return;
  }

  const maxValue = Math.max(...Object.values(data));

  let html = '<div style="padding: 1rem;">';

  Object.entries(data)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cls, value]) => {
      const namePL = getClassNamePL(cls);
      const color = getClassColor(cls);
      const percentage = maxValue > 0 ? (value / maxValue) * 100 : 0;
      const displayValue = value.toFixed(6);

      html += `
        <div style="margin-bottom: 1rem;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
            <div style="display: flex; align-items: center; gap: 0.5rem;">
              <div style="width: 16px; height: 16px; background: ${color}; border: 1px solid var(--border-color); border-radius: 2px;"></div>
              <span style="font-size: 0.875rem; font-weight: 500;">${namePL}</span>
            </div>
            <span style="font-size: 0.875rem; font-weight: 600;">${displayValue}</span>
          </div>
          <div style="width: 100%; height: 24px; background: var(--bg-light); border-radius: 4px; overflow: hidden;">
            <div style="height: 100%; background: ${color}; width: ${percentage}%; transition: width 0.6s ease;"></div>
          </div>
        </div>
      `;
    });

  html += '</div>';
  container.innerHTML = html;
}

function drawStatsBars(stats) {
  statsBars.innerHTML = "";
  if (!stats || !stats.areas_pct) {
    statsBars.textContent = "Brak danych.";
    return;
  }

  Object.entries(stats.areas_pct)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cls, pct], i) => {
      if (pct <= 0.1) return;
      const namePL = getClassNamePL(cls);
      const color = getClassColor(cls);
      const item = document.createElement("div");
      item.className = "bar-item";
      item.innerHTML = `
        <div class="bar-label">${namePL}: ${pct.toFixed(1)}%</div>
        <div class="bar" style="width:${pct}%;background:${color};height:20px;border-radius:4px;"></div>
      `;
      statsBars.appendChild(item);
    });
}

function drawTopAreas(data) {
  const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const container = document.getElementById('statsBars');
  let showingAll = false;
  const showAllBtn = document.createElement('button');
  showAllBtn.className = "image-control-btn";
  showAllBtn.textContent = "Pokaż wszystkie";

  function render(limit = 3) {
    container.innerHTML = "";
    const subset = showingAll ? sorted : sorted.slice(0, limit);
    const maxValue = sorted[0][1];

    subset.forEach(([cls, area], i) => {
      const namePL = getClassNamePL(cls);
      const pct = (area / maxValue) * 100;
      const color = getClassColor(cls);
      const item = document.createElement('div');
      item.style.marginBottom = '0.75rem';
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.875rem;">
          <span><strong>${i + 1}.</strong> ${namePL}</span>
          <span style="color: ${color}"><strong>${area.toFixed(2)} km²</strong></span>
        </div>
        <div style="height: 20px; width: ${pct}%; background: ${color}; border-radius: 4px; transition: width 0.5s ease;"></div>
      `;
      container.appendChild(item);
    });

    if (sorted.length > limit) {
      container.appendChild(showAllBtn);
    }
  }

  showAllBtn.onclick = () => {
    showingAll = !showingAll;
    showAllBtn.textContent = showingAll ? "Pokaż 3 największe" : "Pokaż wszystkie";
    render();
  };

  render();
}

export function initializeSplitter(map) {
  const splitter = document.getElementById('splitter');
  const root = document.documentElement;
  const MIN_PERCENT = 25;
  let isDragging = false;

  splitter.addEventListener('mousedown', (e) => {
    isDragging = true;
    document.body.classList.add('no-select');
  });

  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;

    const containerWidth = document.getElementById('main-container').offsetWidth;
    const newMapWidthPx = e.clientX;
    const newMapWidthPct = (newMapWidthPx / containerWidth) * 100;

    if (newMapWidthPct < MIN_PERCENT) {
      root.style.setProperty('--map-width', `${MIN_PERCENT}%`);
      root.style.setProperty('--results-width', `${100 - MIN_PERCENT}%`);
    } else if (newMapWidthPct > (100 - MIN_PERCENT)) {
      root.style.setProperty('--map-width', `${100 - MIN_PERCENT}%`);
      root.style.setProperty('--results-width', `${MIN_PERCENT}%`);
    } else {
      root.style.setProperty('--map-width', `${newMapWidthPct}%`);
      root.style.setProperty('--results-width', `${100 - newMapWidthPct}%`);
    }

    map.invalidateSize();
  });

  document.addEventListener('mouseup', () => {
    isDragging = false;
    document.body.classList.remove('no-select');
  });
}

export function showParamModal() {
  paramModal.showModal();
}

export function setupModalControls(clearDrawnItems) {
  document.getElementById('cancelBtn').onclick = () => {
    paramModal.close();
    clearDrawnItems();
  };
  document.getElementById('downloadJsonBtn').addEventListener('click', downloadStats);
  document.getElementById('viewRawJsonBtn').addEventListener('click', viewRawStats);
}