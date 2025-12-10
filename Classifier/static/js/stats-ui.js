const statsBars = document.getElementById("statsBars");
const downloadJsonBtn = document.getElementById("downloadJsonBtn");
const viewRawJsonBtn = document.getElementById("viewRawJsonBtn");
let currentStats = null;
let currentImages = null; // Store all images

// Get color and Polish name for class
function getClassColor(className) {
  return window.AppConfig?.classColors?.[className] || "#999";
}

function getClassNamePL(className) {
  return window.AppConfig?.classNamesPL?.[className] || className;
}

export function displayResults({ stats, tabs, original_image, mask_image, preview_image }) {
  currentStats = stats || {};
  currentImages = {
    original: original_image,
    mask: mask_image,
    blended: preview_image
  };

  // Show images card
  const imagesCard = document.getElementById('imagesCard');
  if (imagesCard) {
    imagesCard.style.display = 'block';
  }

  // Set images
  if (original_image) {
    const origImg = document.getElementById('originalImage');
    if (origImg) origImg.src = original_image;
  }
  if (mask_image) {
    const maskImg = document.getElementById('maskImage');
    if (maskImg) maskImg.src = mask_image;
  }
  if (preview_image) {
    const blendImg = document.getElementById('blendedImage');
    if (blendImg) blendImg.src = preview_image;
  }

  // Setup image controls
  setupImageControls();

  if (tabs && tabs.length > 0) createTabs(tabs);
  else drawStatsBars({ areas_pct: stats.areas_pct || {} });

  if (downloadJsonBtn) downloadJsonBtn.onclick = downloadStats;
  if (viewRawJsonBtn) viewRawJsonBtn.onclick = viewRawStats;
  if (downloadJsonBtn) downloadJsonBtn.style.display = "inline-block";
  if (viewRawJsonBtn) viewRawJsonBtn.style.display = "inline-block";
}

function setupImageControls() {
  const buttons = document.querySelectorAll('.image-control-btn[data-view]');
  const layers = document.querySelectorAll('.image-layer');
  const downloadBtn = document.getElementById('downloadActiveBtn');

  let activeView = 'original';

  buttons.forEach(btn => {
    btn.addEventListener('click', () => {
      const view = btn.dataset.view;

      // Update active button
      buttons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      // Update active layer
      layers.forEach(layer => {
        if (layer.dataset.layer === view) {
          layer.classList.add('active');
          layer.style.opacity = '1';
        } else {
          layer.classList.remove('active');
          layer.style.opacity = '0';
        }
      });

      activeView = view;
      if (downloadBtn) downloadBtn.style.display = 'block';
    });
  });

  // Download active image
  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const imageMap = {
        'original': currentImages.original,
        'mask': currentImages.mask,
        'blended': currentImages.blended
      };
      const imageSrc = imageMap[activeView];
      if (imageSrc) {
        const a = document.createElement('a');
        a.href = imageSrc;
        a.download = `landcover_${activeView}_${Date.now()}.png`;
        a.click();
      }
    });
  }

  // Zoom on click
  const images = document.querySelectorAll('.image-layer img');
  images.forEach(img => {
    img.addEventListener('click', () => {
      if (img.style.cursor === 'zoom-in') {
        img.style.maxWidth = 'none';
        img.style.maxHeight = 'none';
        img.style.cursor = 'zoom-out';
        img.parentElement.style.overflow = 'auto';
      } else {
        img.style.maxWidth = '100%';
        img.style.maxHeight = '100%';
        img.style.cursor = 'zoom-in';
        img.parentElement.style.overflow = 'hidden';
      }
    });
  });
}

export function viewRawStats() {
  if (!currentStats) return;
  const blob = new Blob([JSON.stringify(currentStats, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  window.open(url, "_blank");
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function downloadStats() {
  if (!currentStats) return;
  const blob = new Blob([JSON.stringify(currentStats, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "landcover_stats.json";
  a.click();
  URL.revokeObjectURL(url);
}

// ========== TABs ==========
function createTabs(tabs) {
  const tabsHeader = document.getElementById("tabsHeader");
  if (!tabsHeader) return;
  tabsHeader.innerHTML = "";

  const filtered = tabs.filter((t) => t.key !== "adjacency");
  filtered.forEach((tab, i) => {
    const btn = document.createElement("button");
    btn.textContent = tab.label;
    btn.className = "tab-btn" + (i === 0 ? " active" : "");
    btn.onclick = () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      showTabContent(tab);
    };
    tabsHeader.appendChild(btn);
  });

  if (filtered.length > 0) showTabContent(filtered[0]);
}

function showTabContent(tab) {
  const container = document.getElementById("statsBars");
  container.innerHTML = "";

  if (!tab.data || Object.keys(tab.data).length === 0) {
    container.textContent = "Brak danych.";
    return;
  }

  if (tab.key === "percentage") return drawStatsBars({ areas_pct: tab.data });
  if (tab.key === "area") return drawTopAreas(tab.data);

  const table = document.createElement("table");
  table.className = "simple-table";
  for (const [k, v] of Object.entries(tab.data)) {
    const row = document.createElement("tr");
    const val = typeof v === "number" ? v.toFixed(3) : v;
    const namePL = getClassNamePL(k);
    row.innerHTML = `<td>${namePL}</td><td style="text-align:right;">${val}</td>`;
    table.appendChild(row);
  }
  container.appendChild(table);
}

function drawStatsBars(stats) {
  statsBars.innerHTML = "";
  if (!stats || !stats.areas_pct) {
    statsBars.textContent = "Brak danych.";
    return;
  }

  Object.entries(stats.areas_pct)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cls, pct]) => {
      if (!pct || pct < 0.1) return; // skip near zero

      const color = getClassColor(cls);
      const namePL = getClassNamePL(cls);

      const item = document.createElement("div");
      item.className = "bar-item";
      item.innerHTML = `
        <div class="bar-label">${namePL}: ${pct.toFixed(1)}%</div>
        <div class="bar" style="width:${pct}%;background:${color};height:12px;border-radius:6px;"></div>
      `;
      statsBars.appendChild(item);
    });
}

function drawTopAreas(data) {
  const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
  const container = document.getElementById("statsBars");
  let showingAll = false;
  const showAllBtn = document.createElement("button");
  showAllBtn.className = "show-all-btn";
  showAllBtn.textContent = "Pokaż wszystkie";

  function render(limit = 3) {
    container.innerHTML = "";
    const subset = showingAll ? sorted : sorted.slice(0, limit);
    subset.forEach(([cls, area], i) => {
      const namePL = getClassNamePL(cls);
      const div = document.createElement("div");
      div.className = "top-area-item";
      div.innerHTML = `<span class="rank">${i + 1}.</span> ${namePL}: <b>${area.toFixed(2)} km²</b>`;
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