const paramModal = document.getElementById('paramModal');
const preview = document.getElementById('preview');
const statsBars = document.getElementById('statsBars');
const progressPanel = document.getElementById('progressPanel');
const downloadJsonBtn = document.getElementById('downloadJsonBtn');
const viewRawJsonBtn = document.getElementById('viewRawJsonBtn');
let currentStats = null;

/**
 * UI not freeze fix reset UI if rectangle draw basically
 */
export function resetStatsUI() {
  const tabsHeader = document.getElementById('tabsHeader');
  if (tabsHeader) tabsHeader.innerHTML = "";
  statsBars.innerHTML = "Analiza rozpocznie się po wybraniu strefy, którą chcesz przeanalizować na mapie.";
  downloadJsonBtn.style.display = 'none';
  viewRawJsonBtn.style.display = 'none';
  preview.style.display = 'none';
  currentStats = null;
}

/**
 * step indicator TODO upd actuall state
 * @param {number} index
 */
export function setProgress(index) {
  const steps = progressPanel.querySelectorAll('.progress-step');
  steps.forEach((el, i) => {
    el.classList.remove('done', 'active', 'pending');
    if (i < index) el.classList.add('done');
    else if (i === index) el.classList.add('active');
    else el.classList.add('pending');
  });
}

/**
 * setup for data tabs
 * @param {Object} stats - raw statistics object.
 * @param {Array} tabs - tab configuration array.
 * @param {string} [preview_image] - TODO fix preview
 */
export function displayResults({ stats, tabs, preview_image }) {
  currentStats = stats;
  downloadJsonBtn.style.display = 'inline-block';
  viewRawJsonBtn.style.display = 'inline-block';
  if (tabs && tabs.length > 0) createTabs(tabs);
  else drawStatsBars({ areas_pct: stats });

  if (preview_image) {
    preview.src = preview_image;
    preview.style.display = "block";
    preview.style.opacity = "1";
  } else {
    preview.style.display = 'none';
  }
}
export function viewRawStats() {
  if (!currentStats) return;
  // json in other page GITHUBLIKE code<>/raw/download
  const blob = new Blob([JSON.stringify(currentStats, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);

  const win = window.open(url, '_blank');
  if (win) {
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
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
  const filteredTabs = tabs.filter(t => t.key !== "adjacency");

  filteredTabs.forEach((tab, i) => {
    const btn = document.createElement('button');
    btn.textContent = tab.label;
    btn.className = "tab-btn" + (i === 0 ? " active" : "");
    btn.onclick = () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      showTabContent(tab);
    };
    tabsHeader.appendChild(btn);
  });

  if (filteredTabs.length > 0) showTabContent(filteredTabs[0]);
}

function showTabContent(tab) {
  const container = document.getElementById('statsBars');
  container.innerHTML = "";
  if (!tab.data || Object.keys(tab.data).length === 0) {
    container.textContent = "Brak danych.";
    return;
  }
  if (tab.key === "percentage") return drawStatsBars({ areas_pct: tab.data });
  if (tab.key === "area") return drawTopAreas(tab.data);

  const table = document.createElement('table');
  table.className = "simple-table";
  for (const [k, v] of Object.entries(tab.data)) {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${k}</td><td>${typeof v === 'number' ? v.toFixed(3) : v}</td>`;
    table.appendChild(row);
  }
  container.appendChild(table);
}

// === Percentage bars ===
function drawStatsBars(stats) {
  statsBars.innerHTML = "";
  if (!stats || !stats.areas_pct) {
    statsBars.textContent = "Brak danych.";
    return;
  }

  const colors = [
    "#4caf50", "#2196f3", "#ff9800", "#9c27b0", "#f44336",
    "#00bcd4", "#8bc34a", "#ffeb3b", "#795548", "#607d8b"
  ];

  Object.entries(stats.areas_pct)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cls, pct], i) => {
      if (pct <= 0.1) return;
      const color = colors[i % colors.length];
      const item = document.createElement("div");
      item.className = "bar-item";
      item.innerHTML = `
        <div class="bar-label">${cls}: ${pct.toFixed(1)}%</div>
        <div class="bar" style="width:${pct}%;background:${color};"></div>
      `;
      statsBars.appendChild(item);
    });
}
function drawTopAreas(data) {
  const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const container = document.getElementById('statsBars');
  let showingAll = false;
  const showAllBtn = document.createElement('button');
  showAllBtn.className = "show-all-btn";
  showAllBtn.textContent = "Pokaż wszystkie";

  function render(limit = 3) {
    container.innerHTML = "";
    const subset = showingAll ? sorted : sorted.slice(0, limit);
    subset.forEach(([cls, area], i) => {
      const div = document.createElement('div');
      div.className = "top-area-item";
      div.innerHTML = `<span class="rank">${i + 1}.</span> ${cls}: <b>${area.toFixed(2)} km²</b>`;
      container.appendChild(div);
    });
    if (sorted.length > limit) container.appendChild(showAllBtn);
  }

  showAllBtn.onclick = () => {
    showingAll = !showingAll;
    showAllBtn.textContent = showingAll ? "Pokaż 3 największe" : "Pokaż wszystkie";
    render();
  };

  render();
}


/**
 * fixed splitter 45/55 percent map background
 */
export function initializeSplitter(map) {
    const splitter = document.getElementById('splitter');
    const root = document.documentElement;
    const MIN_PERCENT = 25; // 25% minimum width for either pane
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

/**
 * main module collable - clear area
 * @param {Function} clearDrawnItems -map/main to clear the drawn layer.
 */
export function setupModalControls(clearDrawnItems) {
    document.getElementById('cancelBtn').onclick = () => {
        paramModal.close();
        clearDrawnItems();
    };
    // in main.js
    document.getElementById('downloadJsonBtn').addEventListener('click', downloadStats);
    document.getElementById('viewRawJsonBtn').addEventListener('click', viewRawStats);
}