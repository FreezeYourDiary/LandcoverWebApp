document.addEventListener("DOMContentLoaded", function() {
    const config = window.AppConfig || {};
    const classColors = config.classColors || {};

    const CLASS_NAMES_PL = {
        "AnnualCrop": "Uprawy jednoroczne",
        "Forest": "Las",
        "HerbaceousVegetation": "Roślinność zielna",
        "Highway": "Drogi",
        "Industrial": "Tereny przemysłowe",
        "Pasture": "Pastwiska",
        "PermanentCrop": "Uprawy wieloletnie",
        "Residential": "Tereny mieszkalne",
        "River": "Rzeki",
        "SeaLake": "Jeziora i morza"
    };

    const translateClassName = (name) => CLASS_NAMES_PL[name] || name;

    const getChartColors = (classes) => {
        return classes.map(cls => classColors[cls] || "rgb(128, 128, 128)");
    };

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

    if (config.analysesCount > 1) {
        const analysisSelect = document.getElementById('analysisSelect');
        const analysisInfo = document.getElementById('analysisInfo');

        if (analysisSelect && config.analysesList) {
            config.analysesList.forEach(analysis => {
                const option = document.createElement('option');
                option.value = analysis.id;
                option.textContent = `${analysis.created_at} - ${analysis.mode} (zoom ${analysis.zoom})`;
                option.selected = analysis.is_current;
                analysisSelect.appendChild(option);
            });

            const updateAnalysisInfo = () => {
                const selectedId = parseInt(analysisSelect.value);
                const analysis = config.analysesList.find(a => a.id === selectedId);
                if (analysis) {
                    analysisInfo.innerHTML = `
                        <strong>Tryb:</strong> ${analysis.mode} | 
                        <strong>Zoom:</strong> ${analysis.zoom} | 
                        <strong>Wygładzenie:</strong> ${analysis.smoothing ? 'Tak' : 'Nie'} | 
                        <strong>Model:</strong> ${analysis.model}
                    `;
                }
            };
            updateAnalysisInfo();
            analysisSelect.addEventListener('change', updateAnalysisInfo);
        }
    }

    if (config.hasAnalysis) {
        const stats = config.stats;
        const tabs = config.tabs;
        const polandAverages = config.polandAverages;
        const wojewodztwoName = config.wojewodztwoName;

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
                const percentage = (wojValue * 100).toFixed(2);
                const polandValue = polandAverages ? polandAverages.density : null;

                tableDiv.innerHTML = `
                    <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg-light); border-radius: 4px; font-size: 0.875rem;">
                        <strong>Opis:</strong> Gęstość zabudowy przedstawia stosunek powierzchni terenów mieszkalnych i przemysłowych do całkowitej powierzchni analizowanego obszaru. 
                        Wyższa wartość oznacza silniej zurbanizowany teren.
                    </div>
                    <div style="padding: 2rem; text-align: center;">
                        <div style="font-size: 3rem; font-weight: 700; color: var(--accent-default); margin-bottom: 1rem;">
                            ${percentage}%
                        </div>
                        <div style="color: var(--text-light); margin-bottom: 2rem;">Gęstość zabudowy - ${wojewodztwoName}</div>
                        ${polandValue ? `
                        <div style="font-size: 2rem; font-weight: 600; color: var(--text-light);">
                            ${(polandValue * 100).toFixed(2)}%
                        </div>
                        <div style="color: var(--text-light);">Średnia dla Polski</div>
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

            if (currentTab === 'fragmentation') {
                canvas.style.display = 'none';
                renderFragmentation(tab.data, tableDiv);
                return;
            }

            canvas.style.display = 'block';
            const wojData = tab.data;

            if (currentTab === 'percentage') {
                const classes = Object.keys(wojData);
                const wojValues = classes.map(c => wojData[c] || 0);
                const colors = getChartColors(classes);
                const translatedClasses = classes.map(translateClassName);

                const descriptionHTML = `
                    <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg-light); border-radius: 4px; font-size: 0.875rem;">
                        <strong>Opis:</strong> Procentowy udział pokazuje, jaki procent całkowitej powierzchni zajmuje każda klasa pokrycia terenu. 
                        Wartości sumują się do 100%.
                    </div>
                `;

                if (polandAverages && polandAverages.areas_pct) {
                    const polandValues = classes.map(c => polandAverages.areas_pct[c] || 0);

                    tableDiv.innerHTML = descriptionHTML + `
                        <div style="margin-top: 1rem;">
                            <h4 style="text-align: center; margin-bottom: 1rem;">Porównanie rozkładu powierzchni</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
                                <div>
                                    <canvas id="wojPieChart"></canvas>
                                    <p style="text-align: center; margin-top: 0.5rem; font-weight: 600;">${wojewodztwoName}</p>
                                </div>
                                <div>
                                    <canvas id="polandPieChart"></canvas>
                                    <p style="text-align: center; margin-top: 0.5rem; font-weight: 600;">Polska (średnia)</p>
                                </div>
                            </div>
                        </div>
                    `;

                    const wojPieCtx = document.getElementById('wojPieChart').getContext('2d');
                    new Chart(wojPieCtx, {
                        type: 'pie',
                        data: {
                            labels: translatedClasses,
                            datasets: [{
                                data: wojValues,
                                backgroundColor: colors,
                                borderWidth: 2,
                                borderColor: '#fff'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.parsed.toFixed(2);
                                            return `${label}: ${value}%`;
                                        }
                                    }
                                }
                            }
                        }
                    });

                    const polandPieCtx = document.getElementById('polandPieChart').getContext('2d');
                    new Chart(polandPieCtx, {
                        type: 'pie',
                        data: {
                            labels: translatedClasses,
                            datasets: [{
                                data: polandValues,
                                backgroundColor: colors.map(c => c.replace('rgb', 'rgba').replace(')', ', 0.6)')),
                                borderWidth: 2,
                                borderColor: '#fff'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: true,
                            plugins: {
                                legend: {
                                    display: true,
                                    position: 'right',
                                    labels: {
                                        boxWidth: 12,
                                        font: { size: 10 }
                                    }
                                },
                                tooltip: {
                                    callbacks: {
                                        label: function(context) {
                                            const label = context.label || '';
                                            const value = context.parsed.toFixed(2);
                                            return `${label}: ${value}%`;
                                        }
                                    }
                                }
                            }
                        }
                    });

                } else {
                    tableDiv.innerHTML = descriptionHTML;
                    currentChart = new Chart(canvas, {
                        type: 'pie',
                        data: {
                            labels: translatedClasses,
                            datasets: [{
                                data: wojValues,
                                backgroundColor: colors,
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
                                    text: 'Rozkład pokrycia terenu (%)'
                                }
                            }
                        }
                    });
                }
            }
            else if (currentTab === 'area') {
                canvas.style.display = 'none';

                const descriptionHTML = `
                    <div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg-light); border-radius: 4px; font-size: 0.875rem;">
                        <strong>Opis:</strong> Rzeczywista powierzchnia w kilometrach kwadratowych zajmowana przez każdą klasę pokrycia terenu. 
                        Obliczenia uwzględniają współrzędne geograficzne i poziom powiększenia mapy.
                    </div>
                `;
                tableDiv.innerHTML = descriptionHTML;

                renderAreaBars(wojData, tableDiv);
            }
        }

        function renderAreaBars(data, container) {
            const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
            let showingAll = false;

            const showAllBtn = document.createElement('button');
            showAllBtn.className = 'show-all-btn';
            showAllBtn.textContent = 'Pokaż wszystkie';

            const contentDiv = document.createElement('div');
            container.appendChild(contentDiv);

            function render(limit = 3) {
                contentDiv.innerHTML = '';
                const subset = showingAll ? sorted : sorted.slice(0, limit);
                const maxValue = sorted[0][1];

                subset.forEach(([cls, area], i) => {
                    const pct = (area / maxValue) * 100;
                    const color = classColors[cls] || "rgb(128, 128, 128)";
                    const translatedName = translateClassName(cls);

                    const item = document.createElement('div');
                    item.style.marginBottom = '0.75rem';
                    item.innerHTML = `
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.25rem; font-size: 0.875rem;">
                            <span><strong>${i + 1}.</strong> ${translatedName}</span>
                            <span style="color: ${color}"><strong>${area.toFixed(2)} km²</strong></span>
                        </div>
                        <div style="height: 20px; width: ${pct}%; background: ${color}; border-radius: 4px; transition: width 0.5s ease;"></div>
                    `;
                    contentDiv.appendChild(item);
                });

                if (sorted.length > limit) {
                    contentDiv.appendChild(showAllBtn);
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
            if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
                container.innerHTML = '<p style="text-align:center;color:var(--text-light);">Brak danych macierzy sąsiedztwa</p>';
                return;
            }

            const classes = Object.keys(data);
            let html = '<div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg-light); border-radius: 4px; font-size: 0.875rem;">';
            html += '<strong>Opis:</strong> Macierz sąsiedztwa pokazuje, jak często różne klasy pokrycia terenu graniczą ze sobą. ';
            html += 'Wartości przedstawiają proporcję granic. Wyższe wartości (ciemniejszy kolor) oznaczają częstsze sąsiedztwo między klasami.';
            html += '</div>';

            html += '<div style="overflow-x: auto;"><table class="simple-table" style="border-collapse: collapse;"><tr><th style="padding: 8px; border: 1px solid var(--border-color); background: var(--bg-light);"></th>';

            classes.forEach(c => {
                const translatedName = translateClassName(c);
                html += `<th style="padding: 8px; border: 1px solid var(--border-color); background: var(--bg-light); font-size: 0.75rem;">${translatedName}</th>`;
            });
            html += '</tr>';

            classes.forEach(class1 => {
                const name1 = translateClassName(class1);
                html += `<tr><th style="padding: 8px; border: 1px solid var(--border-color); background: var(--bg-light); text-align: left; font-size: 0.75rem;">${name1}</th>`;
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

        function renderFragmentation(data, container) {
            if (!data || typeof data !== 'object' || Object.keys(data).length === 0) {
                container.innerHTML = '<p style="text-align:center;color:var(--text-light);">Brak danych fragmentacji</p>';
                return;
            }

            const sorted = Object.entries(data).sort((a, b) => b[1] - a[1]);
            const maxValue = sorted[0][1];

            let html = '<div style="padding: 1rem;">';
            html += '<div style="margin-bottom: 1.5rem; padding: 1rem; background: var(--bg-light); border-radius: 4px; font-size: 0.875rem;">';
            html += '<strong>Opis:</strong> Indeks fragmentacji to stosunek liczby oddzielnych obszarów danej klasy do jej całkowitej powierzchni. ';
            html += 'Wyższa wartość oznacza bardziej pofragmentowany krajobraz (więcej małych, rozproszonych obszarów).';
            html += '</div>';

            sorted.forEach(([cls, value]) => {
                const translatedName = translateClassName(cls);
                const color = classColors[cls] || "rgb(128, 128, 128)";
                const pct = (value / maxValue) * 100 * 100;
                const displayValue = (value < 0.001 ? value.toExponential(3) : value.toFixed(6));

                html += `
                    <div style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.25rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <div style="width: 16px; height: 16px; background: ${color}; border: 1px solid var(--border-color); border-radius: 2px;"></div>
                                <span style="font-size: 0.875rem; font-weight: 500;">${translatedName}</span>
                            </div>
                            <span style="font-size: 0.875rem; font-weight: 600;">${displayValue}</span>
                        </div>
                        <div style="width: 100%; height: 24px; background: var(--bg-light); border-radius: 4px; overflow: hidden;">
                            <div style="height: 100%; background: ${color}; width: ${pct}%; transition: width 0.5s ease;"></div>
                        </div>
                    </div>
                `;
            });

            html += '</div>';
            container.innerHTML = html;
        }

        renderStats();
    }
});