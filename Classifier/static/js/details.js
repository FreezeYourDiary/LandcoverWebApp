document.addEventListener("DOMContentLoaded", function() {
    const config = window.AppConfig || {};
    const colors = config.colors || [
      "#4caf50", "#2196f3", "#ff9800", "#9c27b0", "#f44336",
      "#00bcd4", "#8bc34a", "#ffeb3b", "#795548", "#607d8b"
    ];

    // splitter init
    const splitter = document.getElementById('splitter');
    const root = document.documentElement;
    const MIN_PERCENT = 25;
    let isDragging = false;
    root.style.setProperty('--results-width', '75%');
    root.style.setProperty('--map-width', '25%');

    splitter.addEventListener('mousedown', (e) => {
        isDragging = true;
        document.body.classList.add('no-select');
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;

        const containerWidth = document.getElementById('main-container').offsetWidth;
        const newResultsWidthPx = e.clientX;
        const newResultsWidthPct = (newResultsWidthPx / containerWidth) * 100;

        if (newResultsWidthPct < MIN_PERCENT) {
            root.style.setProperty('--results-width', `${MIN_PERCENT}%`);
            root.style.setProperty('--map-width', `${100 - MIN_PERCENT}%`);
        } else if (newResultsWidthPct > (100 - MIN_PERCENT)) {
            root.style.setProperty('--results-width', `${100 - MIN_PERCENT}%`);
            root.style.setProperty('--map-width', `${MIN_PERCENT}%`);
        } else {
            root.style.setProperty('--results-width', `${newResultsWidthPct}%`);
            root.style.setProperty('--map-width', `${100 - newResultsWidthPct}%`);
        }
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
        document.body.classList.remove('no-select');
    });

    document.querySelectorAll('.image-control-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.dataset.view;

            document.querySelectorAll('.image-control-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            document.querySelectorAll('.image-layer').forEach(layer => {
                layer.style.opacity = '0';
            });
            document.querySelector(`[data-layer="${view}"]`).style.opacity = '1';
        });
    });

    if (config.hasAnalysis) {
        const stats = config.stats;
        const tabs = config.tabs;
        const polandAverages = config.polandAverages;
        const wojewodztwoName = config.wojewodztwoName; // vpases todo tracing by name

        let currentTab = 'percentage';
        let currentChart = null;

        document.getElementById('downloadBtn').addEventListener('click', () => {
            const blob = new Blob([JSON.stringify(stats, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${wojewodztwoName}_stats.json`;
            a.click();
            URL.revokeObjectURL(url);
        });

        document.getElementById('viewRawBtn').addEventListener('click', () => {
            const win = window.open('', '_blank');
            win.document.write('<pre>' + JSON.stringify(stats, null, 2) + '</pre>');
        });

        const tabsHeader = document.getElementById('tabsHeader');
        tabs.forEach(tab => {
            const btn = document.createElement('button');
            btn.className = 'tab-btn';
            if (tab.key === currentTab) btn.classList.add('active');
            btn.textContent = tab.label;
            btn.addEventListener('click', () => {
                currentTab = tab.key;
                document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderStats();
            });
            tabsHeader.appendChild(btn);
        });

        function renderStats() {
            const tab = tabs.find(t => t.key === currentTab);
            if (!tab) return;

            if (currentChart) {
                currentChart.destroy();
                currentChart = null;
            }

            const canvas = document.getElementById('statsChart');
            const tableDiv = document.getElementById('statsTable');
            tableDiv.innerHTML = '';

            if (currentTab === 'density') {
                canvas.style.display = 'none';
                const wojValue = tab.data || 0;
                const polandValue = polandAverages ? polandAverages.density : null;

                tableDiv.innerHTML = `
                    <div style="padding: 2rem; text-align: center;">
                    <div style="font-size: 3rem; font-weight: 700; color: var(--accent-default); margin-bottom: 1rem;">
                        ${wojValue.toFixed(4)}
                    </div>
                    <div style="color: var(--text-light); margin-bottom: 2rem;"> Gęstość </div>
                    ${polandValue ? `
                    <div style="font-size: 2rem; font-weight: 600; color: var(--text-light);">
                        ${polandValue.toFixed(4)}
                    </div>
                    <div style="color: var(--text-light);"> Srednia dla Polski </div>
                    ` : ''}
                    </div>
                `;
                return;
            }
            if (currentTab === 'adjacency') {
                canvas.style.display = 'none';
                renderAdjacencyMatrix(tab.data, tableDiv);
                return;
            }

            canvas.style.display = 'block';
            const wojData = tab.data;

            if (currentTab === 'percentage') {
                const classes = Object.keys(wojData);
                const wojValues = classes.map(c => wojData[c] || 0);

                currentChart = new Chart(canvas, {
                    type: 'pie',
                    data: {
                        labels: classes,
                        datasets: [{
                            data: wojValues,
                            backgroundColor: colors.slice(0, classes.length),
                            borderWidth: 2,
                            borderColor: '#fff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { position: 'right' },
                            title: {
                                display: true,
                                text: 'Land Cover Distribution (%)'
                            }
                        }
                    }
                });
            }
            else if (currentTab === 'area') {
                canvas.style.display = 'none';
                renderAreaBars(wojData, tableDiv);
            }
        }

        function renderAreaBars(data, container) {
            const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
            let showingAll = false;

            const showAllBtn = document.createElement('button');
            showAllBtn.className = 'show-all-btn';
            showAllBtn.textContent = 'Pokaż wszystkie';

            function render(limit = 3) {
                container.innerHTML = '';
                const subset = showingAll ? sorted : sorted.slice(0, limit);
                const maxValue = sorted[0][1];

                subset.forEach(([cls, area], i) => {
                    const pct = (area / maxValue) * 100;
                    const color = colors[i % colors.length];

                    const item = document.createElement('div');
                    item.style.marginBottom = '0.75rem';
                    item.innerHTML = `
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.875rem;">
                        <span><strong>${i + 1}.</strong> ${cls}</span>
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
                showAllBtn.textContent = showingAll ? 'Pokaż 3 największe' : 'Pokaż wszystkie';
                render();
            };

            render();
        }

        function renderAdjacencyMatrix(data, container) {
            if (!data || typeof data !== 'object') {
                container.innerHTML = '<p style="text-align:center;color:var(--text-light);">No adjacency data</p>';
                return;
            }

            const classes = Object.keys(data);
            let html = '<table class="simple-table"><tr><th></th>';

            classes.forEach(c => html += `<th>${c}</th>`);
            html += '</tr>';

            classes.forEach(class1 => {
                html += `<tr><th>${class1}</th>`;
                classes.forEach(class2 => {
                    const value = data[class1]?.[class2] || 0;
                    const intensity = Math.min(value / 0.2, 1);
                    const bgColor = `rgba(52, 152, 219, ${intensity * 0.7})`;
                    html += `<td style="background: ${bgColor}; padding: 8px;">${value.toFixed(4)}</td>`;
                });
                html += '</tr>';
            });

            html += '</table>';
            container.innerHTML = html;
        }

        renderStats();
    }
});