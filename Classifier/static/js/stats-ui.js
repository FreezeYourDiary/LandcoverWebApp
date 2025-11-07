const statsBars = document.getElementById("statsBars");
const preview = document.getElementById("preview");
const downloadJsonBtn = document.getElementById("downloadJsonBtn");
const viewRawJsonBtn = document.getElementById("viewRawJsonBtn");
let currentStats = null;

export function displayResults({ stats, tabs, preview_image }) {
  currentStats = stats || {};
  if (tabs && tabs.length > 0) createTabs(tabs);
  else drawStatsBars({ areas_pct: stats.areas_pct || {} });

  if (preview_image) {
    preview.src = preview_image;
    preview.style.display = "block";
    preview.style.opacity = "1";
  }

  if (downloadJsonBtn) downloadJsonBtn.onclick = downloadStats;
  if (viewRawJsonBtn) viewRawJsonBtn.onclick = viewRawStats;
  if (downloadJsonBtn) downloadJsonBtn.style.display = "inline-block";
  if (viewRawJsonBtn) viewRawJsonBtn.style.display = "inline-block";
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
    row.innerHTML = `<td>${k}</td><td style="text-align:right;">${val}</td>`;
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

  const colors = [
    "#4caf50", "#2196f3", "#ff9800", "#9c27b0", "#f44336",
    "#00bcd4", "#8bc34a", "#ffeb3b", "#795548", "#607d8b"
  ];

  Object.entries(stats.areas_pct)
    .sort((a, b) => b[1] - a[1])
    .forEach(([cls, pct], i) => {
      if (!pct || pct < 0.1) return; // skip near zero
      const color = colors[i % colors.length];
      const item = document.createElement("div");
      item.className = "bar-item";
      item.innerHTML = `
        <div class="bar-label">${cls}: ${pct.toFixed(1)}%</div>
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
      const div = document.createElement("div");
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
