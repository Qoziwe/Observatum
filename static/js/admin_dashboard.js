(function () {
    let currentPayload = window.__INITIAL_PAYLOAD__ || null;
    let charts = {};
    let socket = null;
    let manualPaused = false;

    function getThemePalette() {
        const isDark = document.documentElement.getAttribute("data-theme") !== "light";
        return {
            isDark: isDark,
            ink: isDark ? "#F3F5FA" : "#151821",
            secondary: isDark ? "#B4BCD0" : "#434B5E",
            muted: isDark ? "#768096" : "#737C91",
            panel: isDark ? "#171A24" : "#FFFFFF",
            elevated: isDark ? "#1F2330" : "#F2F5FA",
            grid: isDark ? "rgba(255,255,255,0.06)" : "rgba(21,24,33,0.07)",
            border: isDark ? "rgba(255,255,255,0.14)" : "rgba(21,24,33,0.16)",
            rose: "#FF5470",
            cyan: "#7DCFFF",
            lavender: "#BB9AF7",
            mint: "#9ECE6A",
            amber: "#E0AF68",
            blue: "#7AA2F7",
            teal: "#73DACA",
            seriesColors: [
                "#FF5470",
                "#7DCFFF",
                "#BB9AF7",
                "#9ECE6A",
                "#E0AF68",
                "#7AA2F7",
                "#73DACA"
            ]
        };
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = String(str || "");
        return div.innerHTML;
    }

    function ensureChart(domId) {
        const el = document.getElementById(domId);
        if (!el) return null;
        if (!charts[domId]) {
            charts[domId] = echarts.init(el);
        }
        return charts[domId];
    }

    function baseTextStyle(pal) {
        return {
            fontFamily: "Inter, -apple-system, sans-serif",
            color: pal.secondary,
            fontSize: 11
        };
    }

    function baseTooltip(pal) {
        return {
            backgroundColor: pal.panel,
            borderColor: pal.border,
            borderWidth: 1,
            borderRadius: 12,
            padding: [10, 14],
            textStyle: {
                color: pal.ink,
                fontFamily: "Inter, sans-serif",
                fontSize: 12
            }
        };
    }

    function updateKPIs(kpis, listeners) {
        const setTxt = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };
        setTxt("kpiTotal", kpis.total);
        setTxt("kpiTotalSub", `Real: ${kpis.real_count} • Demo: ${kpis.demo_count}`);
        setTxt("kpiPain", `${kpis.composite_pain_index} / 100`);
        setTxt("kpiFrustration", `${kpis.mean_frustration} / 5.0`);
        setTxt("kpiFrustrationSub", `Med: ${kpis.median_frustration} • High(4-5): ${kpis.high_frustration_pct}%`);
        setTxt("kpiDailyDrop", `${kpis.daily_disconnect_pct}%`);
        setTxt("kpiPhantom", `${kpis.phantom_signal_pct}%`);
        setTxt("kpiUnfairPrice", `${kpis.unfair_price_pct}%`);
        setTxt("kpiSupportPain", `${kpis.support_pain_pct}%`);
        setTxt("kpiPitch", `${kpis.pitch_approval_pct}%`);
        setTxt("kpiPitchSub", `Definite Yes: ${kpis.pitch_definite_pct}%`);
        setTxt("listenerCountBadge", `Listeners: ${listeners || 1}`);
    }

    function renderAllCharts(data) {
        if (!data) return;
        const pal = getThemePalette();
        const colors = pal.seriesColors;

        // 1. SANKEY
        const cSankey = ensureChart("chartSankey");
        if (cSankey) {
            const sk = data.cross.sankey;
            cSankey.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "item", triggerOn: "mousemove" }, baseTooltip(pal)),
                series: [{
                    type: "sankey",
                    emphasis: { focus: "adjacency" },
                    nodeAlign: "justify",
                    data: sk.nodes.length ? sk.nodes : [{ name: "No Data Yet" }],
                    links: sk.links,
                    lineStyle: { color: "gradient", curveness: 0.45, opacity: 0.42 },
                    itemStyle: { borderWidth: 0, borderRadius: 4 },
                    label: { color: pal.ink, fontFamily: "Inter, sans-serif", fontSize: 11, fontWeight: 500 }
                }],
                color: colors
            }, true);
        }

        // 2. COMPOSITE PAIN GAUGE
        const cGauge = ensureChart("chartGauge");
        if (cGauge) {
            cGauge.setOption({
                textStyle: baseTextStyle(pal),
                series: [{
                    type: "gauge",
                    min: 0,
                    max: 100,
                    splitNumber: 5,
                    radius: "88%",
                    axisLine: {
                        roundCap: true,
                        lineStyle: {
                            width: 14,
                            color: [
                                [0.35, pal.mint],
                                [0.68, pal.amber],
                                [1, pal.rose]
                            ]
                        }
                    },
                    pointer: { itemStyle: { color: pal.cyan }, width: 5 },
                    axisTick: { distance: -18, length: 5, lineStyle: { color: pal.muted, width: 1 } },
                    splitLine: { distance: -20, length: 12, lineStyle: { color: pal.secondary, width: 2 } },
                    axisLabel: { color: pal.secondary, distance: 22, fontSize: 10, fontFamily: "JetBrains Mono, monospace" },
                    detail: {
                        valueAnimation: true,
                        formatter: "{value}",
                        color: pal.ink,
                        fontSize: 32,
                        fontWeight: 700,
                        fontFamily: "JetBrains Mono, monospace",
                        offsetCenter: [0, "62%"]
                    },
                    title: {
                        offsetCenter: [0, "88%"],
                        fontSize: 11,
                        color: pal.secondary,
                        fontFamily: "Inter, sans-serif"
                    },
                    data: [{ value: data.kpis.composite_pain_index, name: "KL Pain Index (0–100)" }]
                }]
            }, true);
        }

        // 3. HEATMAP: Mobile Provider x Disconnection Frequency
        const cHmMob = ensureChart("chartHeatmapMobile");
        if (cHmMob) {
            const hm = data.cross.heatmap_mobile_freq;
            const maxVal = Math.max(1, ...hm.points.map(p => p[2]));
            cHmMob.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ position: "top" }, baseTooltip(pal)),
                grid: { left: 125, right: 20, top: 18, bottom: 64 },
                xAxis: {
                    type: "category",
                    data: hm.freq_labels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.secondary, rotate: 15, fontSize: 10 }
                },
                yAxis: {
                    type: "category",
                    data: hm.mobile_labels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.ink, fontSize: 11, fontWeight: 500 }
                },
                visualMap: {
                    min: 0,
                    max: maxVal,
                    calculable: false,
                    orient: "horizontal",
                    left: "center",
                    bottom: 0,
                    inRange: {
                        color: pal.isDark
                            ? ["#1A1E2B", "#52467A", "#BB9AF7", "#FF5470"]
                            : ["#EEF2F8", "#9CC2F5", "#7AA2F7", "#E93D58"]
                    },
                    textStyle: { color: pal.secondary, fontSize: 10 }
                },
                series: [{
                    name: "Respondents",
                    type: "heatmap",
                    data: hm.points,
                    label: { show: true, color: pal.ink, fontWeight: 600, fontSize: 11 },
                    itemStyle: { borderColor: pal.panel, borderWidth: 3, borderRadius: 6 }
                }]
            }, true);
        }

        // 4. MOBILE OPERATOR SHARE vs MEAN FRUSTRATION
        const cMobFrust = ensureChart("chartMobileFrustration");
        if (cMobFrust) {
            const mobDist = data.distributions.q5_mobile_provider;
            const avgF = data.cross.heatmap_mobile_freq.mobile_avg_frustration;
            cMobFrust.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" } }, baseTooltip(pal)),
                legend: { textStyle: { color: pal.secondary, fontSize: 11 }, top: 0 },
                grid: { left: 118, right: 48, top: 36, bottom: 28 },
                xAxis: [
                    { type: "value", name: "Users", axisLabel: { color: pal.muted }, splitLine: { lineStyle: { color: pal.grid } } },
                    { type: "value", name: "Stress", min: 0, max: 5, axisLabel: { color: pal.rose }, splitLine: { show: false } }
                ],
                yAxis: {
                    type: "category",
                    data: mobDist.labels,
                    inverse: true,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.ink, fontSize: 11, fontWeight: 500 }
                },
                series: [
                    {
                        name: "Users (N)",
                        type: "bar",
                        data: mobDist.counts,
                        itemStyle: { color: pal.cyan, borderRadius: [0, 6, 6, 0] }
                    },
                    {
                        name: "Avg Frustration (1–5)",
                        type: "bar",
                        xAxisIndex: 1,
                        data: avgF,
                        itemStyle: { color: pal.rose, borderRadius: [0, 6, 6, 0] },
                        label: { show: true, position: "right", color: pal.ink, fontWeight: 600, fontSize: 11 }
                    }
                ]
            }, true);
        }

        // 5. FIXED BROADBAND VS VALUE PERCEPTION
        const cBrd = ensureChart("chartBroadbandValue");
        if (cBrd) {
            const bv = data.cross.broadband_vs_value;
            const stackColors = [pal.rose, pal.amber, pal.lavender, pal.cyan, pal.mint];
            const series = bv.value_labels.map((vLabel, vIdx) => ({
                name: vLabel,
                type: "bar",
                stack: "total",
                emphasis: { focus: "series" },
                itemStyle: { color: stackColors[vIdx % stackColors.length] },
                data: bv.broadband_labels.map((_, bIdx) => bv.matrix[bIdx][vIdx])
            }));
            cBrd.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" } }, baseTooltip(pal)),
                legend: { textStyle: { color: pal.secondary, fontSize: 10 }, top: 0 },
                grid: { left: 148, right: 20, top: 44, bottom: 26 },
                xAxis: { type: "value", axisLabel: { color: pal.muted }, splitLine: { lineStyle: { color: pal.grid } } },
                yAxis: { type: "category", data: bv.broadband_labels, inverse: true, axisLine: { lineStyle: { color: pal.border } }, axisLabel: { color: pal.ink, fontSize: 11, fontWeight: 500 } },
                series: series
            }, true);
        }

        // 6. KLANG VALLEY ZONE VULNERABILITY
        const cArea = ensureChart("chartAreaVulnerability");
        if (cArea) {
            const av = data.cross.area_vulnerability;
            const zLabels = av.map(x => x.area);
            cArea.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" } }, baseTooltip(pal)),
                legend: { textStyle: { color: pal.secondary, fontSize: 10 }, top: 0 },
                grid: { left: 42, right: 20, top: 42, bottom: 70 },
                xAxis: {
                    type: "category",
                    data: zLabels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.secondary, rotate: 18, fontSize: 10 }
                },
                yAxis: {
                    type: "value",
                    max: 100,
                    axisLabel: { color: pal.muted },
                    splitLine: { lineStyle: { color: pal.grid } }
                },
                series: [
                    {
                        name: "Daily Drops %",
                        type: "bar",
                        data: av.map(x => x.daily_drop_pct),
                        itemStyle: { color: pal.rose, borderRadius: [5, 5, 0, 0] }
                    },
                    {
                        name: "Phantom Signal %",
                        type: "bar",
                        data: av.map(x => x.phantom_pct),
                        itemStyle: { color: pal.lavender, borderRadius: [5, 5, 0, 0] }
                    },
                    {
                        name: "Zone Pain Index",
                        type: "line",
                        smooth: true,
                        lineStyle: { width: 3, color: pal.cyan },
                        itemStyle: { color: pal.cyan },
                        data: av.map(x => x.pain_index)
                    }
                ]
            }, true);
        }

        // 7. PHANTOM SIGNAL POLAR ROSE (Q8)
        const cPhantom = ensureChart("chartPhantomSignal");
        if (cPhantom) {
            const q8 = data.distributions.q8_phantom_signal;
            cPhantom.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "item", formatter: "{b}: {c} ({d}%)" }, baseTooltip(pal)),
                legend: { bottom: 0, textStyle: { color: pal.secondary, fontSize: 10 } },
                series: [{
                    name: "Phantom Signal",
                    type: "pie",
                    radius: ["22%", "68%"],
                    center: ["50%", "44%"],
                    roseType: "area",
                    itemStyle: { borderColor: pal.panel, borderWidth: 2, borderRadius: 6 },
                    label: { color: pal.ink, fontSize: 11, fontWeight: 500, formatter: "{b} ({d}%)" },
                    data: q8.labels.map((lbl, idx) => ({ name: lbl, value: q8.counts[idx] }))
                }],
                color: [pal.rose, pal.amber, pal.cyan, pal.mint]
            }, true);
        }

        // 8. PARETO CHART (Q9)
        const cPareto = ensureChart("chartParetoQ9");
        if (cPareto) {
            const p9 = data.cross.q9_pareto;
            cPareto.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis" }, baseTooltip(pal)),
                legend: { top: 0, textStyle: { color: pal.secondary, fontSize: 11 } },
                grid: { left: 45, right: 45, top: 38, bottom: 68 },
                xAxis: {
                    type: "category",
                    data: p9.labels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.secondary, rotate: 15, fontSize: 10 }
                },
                yAxis: [
                    { type: "value", axisLabel: { color: pal.muted }, splitLine: { lineStyle: { color: pal.grid } } },
                    { type: "value", min: 0, max: 100, axisLabel: { color: pal.cyan, formatter: "{value}%" }, splitLine: { show: false } }
                ],
                series: [
                    {
                        name: "Trigger Mentions",
                        type: "bar",
                        data: p9.counts,
                        itemStyle: { color: pal.lavender, borderRadius: [6, 6, 0, 0] },
                        label: { show: true, position: "top", color: pal.ink, fontWeight: 600, fontSize: 11 }
                    },
                    {
                        name: "Cumulative %",
                        type: "line",
                        smooth: true,
                        yAxisIndex: 1,
                        data: p9.cumulative_pct,
                        lineStyle: { width: 3, color: pal.cyan },
                        itemStyle: { color: pal.cyan }
                    }
                ]
            }, true);
        }

        // 9. FRUSTRATION SCALE (Q10)
        const cFrust = ensureChart("chartFrustrationDist");
        if (cFrust) {
            const fs = data.frustration_scale;
            const scaleColors = [pal.mint, pal.cyan, pal.amber, pal.lavender, pal.rose];
            cFrust.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" } }, baseTooltip(pal)),
                grid: { left: 40, right: 18, top: 26, bottom: 42 },
                xAxis: {
                    type: "category",
                    data: fs.labels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.secondary, fontSize: 10 }
                },
                yAxis: {
                    type: "value",
                    axisLabel: { color: pal.muted },
                    splitLine: { lineStyle: { color: pal.grid } }
                },
                series: [{
                    type: "bar",
                    data: fs.counts.map((v, i) => ({
                        value: v,
                        itemStyle: { color: scaleColors[i], borderRadius: [6, 6, 0, 0] }
                    })),
                    label: { show: true, position: "top", color: pal.ink, fontWeight: 600, fontSize: 12 }
                }]
            }, true);
        }

        // 10. DAILY ACTIVITIES IMPACT RADAR (Q11)
        const cRadar = ensureChart("chartImpactRadar");
        if (cRadar) {
            const q11 = data.distributions.q11_impacted_activities;
            const maxR = Math.max(5, ...q11.counts);
            cRadar.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: baseTooltip(pal),
                radar: {
                    indicator: q11.labels.map(lbl => ({ name: lbl, max: maxR })),
                    axisName: { color: pal.ink, fontFamily: "Inter, sans-serif", fontSize: 10, fontWeight: 500 },
                    splitLine: { lineStyle: { color: pal.grid } },
                    splitArea: { areaStyle: { color: ["transparent"] } },
                    axisLine: { lineStyle: { color: pal.grid } }
                },
                series: [{
                    type: "radar",
                    data: [{
                        value: q11.counts,
                        name: "Impacted Activities",
                        areaStyle: { color: "rgba(125, 207, 255, 0.25)" },
                        lineStyle: { color: pal.cyan, width: 2.5 },
                        itemStyle: { color: pal.cyan }
                    }]
                }]
            }, true);
        }

        // 11. COPING MECHANISMS BREAKDOWN (Q12)
        const cCoping = ensureChart("chartCopingBar");
        if (cCoping) {
            const q12 = data.distributions.q12_coping_mechanisms;
            cCoping.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" } }, baseTooltip(pal)),
                grid: { left: 168, right: 34, top: 18, bottom: 26 },
                xAxis: { type: "value", axisLabel: { color: pal.muted }, splitLine: { lineStyle: { color: pal.grid } } },
                yAxis: { type: "category", data: q12.labels, inverse: true, axisLine: { lineStyle: { color: pal.border } }, axisLabel: { color: pal.ink, fontSize: 10, fontWeight: 500 } },
                series: [{
                    type: "bar",
                    data: q12.counts,
                    itemStyle: { color: pal.amber, borderRadius: [0, 6, 6, 0] },
                    label: { show: true, position: "right", color: pal.ink, fontWeight: 600, fontSize: 11 }
                }]
            }, true);
        }

        // 12. SUPPORT SATISFACTION X PRICE FAIRNESS HEATMAP (Q13 x Q14)
        const cSupHm = ensureChart("chartSupportHeatmap");
        if (cSupHm) {
            const sv = data.cross.heatmap_support_value;
            const maxSV = Math.max(1, ...sv.points.map(p => p[2]));
            cSupHm.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ position: "top" }, baseTooltip(pal)),
                grid: { left: 168, right: 20, top: 18, bottom: 62 },
                xAxis: {
                    type: "category",
                    data: sv.value_labels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.secondary, rotate: 15, fontSize: 10 }
                },
                yAxis: {
                    type: "category",
                    data: sv.support_labels,
                    axisLine: { lineStyle: { color: pal.border } },
                    axisLabel: { color: pal.ink, fontSize: 10, fontWeight: 500 }
                },
                visualMap: {
                    min: 0,
                    max: maxSV,
                    orient: "horizontal",
                    left: "center",
                    bottom: 0,
                    inRange: {
                        color: pal.isDark
                            ? ["#1A1E2B", "#3B5998", "#7DCFFF", "#FF5470"]
                            : ["#EEF2F8", "#9CC2F5", "#3B66E5", "#E93D58"]
                    },
                    textStyle: { color: pal.secondary, fontSize: 10 }
                },
                series: [{
                    type: "heatmap",
                    data: sv.points,
                    label: { show: true, color: pal.ink, fontWeight: 600, fontSize: 11 },
                    itemStyle: { borderColor: pal.panel, borderWidth: 3, borderRadius: 6 }
                }]
            }, true);
        }

        // 13. STEP 9 PITCH: AUTO EMERGENCY 5G BACKUP / BILL REBATE (Q15)
        const cPitch15 = ensureChart("chartPitchQ15");
        if (cPitch15) {
            const q15 = data.distributions.q15_auto_backup_support;
            cPitch15.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "item", formatter: "{b}: {c} ({d}%)" }, baseTooltip(pal)),
                legend: { bottom: 0, textStyle: { color: pal.secondary, fontSize: 10 } },
                series: [{
                    type: "pie",
                    radius: ["44%", "70%"],
                    center: ["50%", "44%"],
                    itemStyle: { borderColor: pal.panel, borderWidth: 3, borderRadius: 8 },
                    label: { color: pal.ink, fontSize: 11, fontWeight: 600, formatter: "{b} ({d}%)" },
                    data: q15.labels.map((lbl, idx) => ({ name: lbl, value: q15.counts[idx] }))
                }],
                color: [pal.mint, pal.amber, pal.rose]
            }, true);
        }

        // 14. STEP 9 PITCH: TOP 2 WANTED IMPROVEMENTS (Q16)
        const cPitch16 = ensureChart("chartPitchQ16");
        if (cPitch16) {
            const q16 = data.distributions.q16_top_improvements;
            cPitch16.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "axis", axisPointer: { type: "shadow" } }, baseTooltip(pal)),
                grid: { left: 192, right: 38, top: 18, bottom: 26 },
                xAxis: { type: "value", axisLabel: { color: pal.muted }, splitLine: { lineStyle: { color: pal.grid } } },
                yAxis: { type: "category", data: q16.labels, inverse: true, axisLine: { lineStyle: { color: pal.border } }, axisLabel: { color: pal.ink, fontSize: 10, fontWeight: 500 } },
                series: [{
                    type: "bar",
                    data: q16.counts,
                    itemStyle: { color: pal.rose, borderRadius: [0, 6, 6, 0] },
                    label: { show: true, position: "right", color: pal.ink, fontWeight: 700, fontSize: 12 }
                }]
            }, true);
        }

        // 15. DEMOGRAPHICS: OCCUPATION (Q3)
        const cOcc = ensureChart("chartOccupation");
        if (cOcc) {
            const q3 = data.distributions.q3_occupation;
            cOcc.setOption({
                textStyle: baseTextStyle(pal),
                tooltip: Object.assign({ trigger: "item", formatter: "{b}: {c} ({d}%)" }, baseTooltip(pal)),
                legend: { bottom: 0, textStyle: { color: pal.secondary, fontSize: 10 } },
                series: [{
                    type: "pie",
                    radius: ["38%", "68%"],
                    center: ["50%", "43%"],
                    itemStyle: { borderColor: pal.panel, borderWidth: 3, borderRadius: 6 },
                    label: { color: pal.ink, fontSize: 11, fontWeight: 500, formatter: "{b}: {c}" },
                    data: q3.labels.map((lbl, idx) => ({ name: lbl, value: q3.counts[idx] }))
                }],
                color: colors
            }, true);
        }
    }

    function renderStoriesAndTable(data) {
        const storiesBox = document.getElementById("storiesContainer");
        if (storiesBox) {
            if (!data.stories || data.stories.length === 0) {
                storiesBox.innerHTML = `<div class="story-slab"><div class="story-quote" style="color: var(--ink-muted);">No field stories submitted in Q17 yet.</div></div>`;
            } else {
                storiesBox.innerHTML = data.stories.map(s => `
                    <article class="story-slab">
                        <div class="story-quote">"${escapeHtml(s.text)}"</div>
                        <div class="story-meta">
                            <span class="story-badge" style="color: var(--accent); border-color: var(--accent);">Stress ${s.frustration}/5</span>
                            <span class="story-badge">${escapeHtml(s.area)}</span>
                            <span class="story-badge">${escapeHtml(s.mobile)}</span>
                            <span class="story-badge">${escapeHtml(s.broadband)}</span>
                            <span class="story-badge">${escapeHtml(s.participant_id)}</span>
                        </div>
                    </article>
                `).join("");
            }
        }

        const tbody = document.getElementById("responsesTableBody");
        if (tbody) {
            if (!data.recent_responses || data.recent_responses.length === 0) {
                tbody.innerHTML = `<tr><td colspan="12" style="text-align:center; padding: 24px;">No survey responses recorded yet</td></tr>`;
            } else {
                tbody.innerHTML = data.recent_responses.map(r => `
                    <tr>
                        <td>#${r.id}</td>
                        <td><strong style="color: var(--cyan);">${escapeHtml(r.receipt_code)}</strong></td>
                        <td>${escapeHtml(r.participant_id)}</td>
                        <td>${r.is_demo ? "Demo" : "Real"}</td>
                        <td>${escapeHtml(r.occupation)}</td>
                        <td>${escapeHtml(r.area)}</td>
                        <td>${escapeHtml(r.mobile)}</td>
                        <td>${escapeHtml(r.broadband)}</td>
                        <td>${escapeHtml(r.disconnect_freq)}</td>
                        <td><strong>${r.frustration} / 5</strong></td>
                        <td>${escapeHtml(r.pitch_support)}</td>
                        <td>
                            <button type="button" class="btn-brutal btn-danger" style="padding: 4px 10px; font-size: 0.7rem;" data-del-id="${r.id}">Delete</button>
                        </td>
                    </tr>
                `).join("");
            }
        }
    }

    function applyFullUpdate(payload) {
        if (!payload) return;
        currentPayload = payload;
        updateKPIs(payload.kpis, payload.active_listeners);
        renderAllCharts(payload);
        renderStoriesAndTable(payload);
    }

    function setWsStatus(state, text) {
        const dot = document.getElementById("wsDot");
        const label = document.getElementById("wsStatusText");
        if (dot) {
            dot.className = "ws-dot " + (state === "live" ? "" : state === "sleep" ? "sleeping" : "offline");
        }
        if (label) {
            label.textContent = text;
        }
    }

    function initSmartWebSocket() {
        socket = io({
            transports: ["websocket", "polling"],
            reconnection: true,
            reconnectionDelay: 2000
        });

        socket.on("connect", function () {
            setWsStatus("live", "Live Stream");
        });

        socket.on("disconnect", function () {
            if (document.hidden || manualPaused) {
                setWsStatus("sleep", "Idle (Battery Saver)");
            } else {
                setWsStatus("offline", "Reconnecting...");
            }
        });

        socket.on("survey_update", function (payload) {
            applyFullUpdate(payload);
        });

        document.addEventListener("visibilitychange", function () {
            if (manualPaused) return;
            if (document.hidden) {
                if (socket && socket.connected) {
                    socket.disconnect();
                }
                setWsStatus("sleep", "Idle (Tab Hidden)");
            } else {
                if (socket && !socket.connected) {
                    socket.connect();
                }
            }
        });
    }

    window.addEventListener("DOMContentLoaded", function () {
        const savedTheme = "dark";
        document.documentElement.setAttribute("data-theme", savedTheme);
        const themeBtn = document.getElementById("themeBtn");
        if (themeBtn) {
            themeBtn.textContent = savedTheme === "dark" ? "Theme: Dark" : "Theme: Light";
            themeBtn.addEventListener("click", function () {
                const cur = document.documentElement.getAttribute("data-theme");
                const next = cur === "dark" ? "light" : "dark";
                document.documentElement.setAttribute("data-theme", next);
                localStorage.setItem("observatum_bento_theme", next);
                themeBtn.textContent = next === "dark" ? "Theme: Dark" : "Theme: Light";
                renderAllCharts(currentPayload);
            });
        }

        if (currentPayload) {
            applyFullUpdate(currentPayload);
        }

        initSmartWebSocket();

        window.addEventListener("resize", function () {
            Object.values(charts).forEach(ch => ch && ch.resize());
        });

        const pauseWsBtn = document.getElementById("pauseWsBtn");
        if (pauseWsBtn) {
            pauseWsBtn.addEventListener("click", function () {
                manualPaused = !manualPaused;
                if (manualPaused) {
                    if (socket) socket.disconnect();
                    pauseWsBtn.textContent = "Resume Live";
                    setWsStatus("sleep", "Paused");
                } else {
                    if (socket) socket.connect();
                    pauseWsBtn.textContent = "Pause Live";
                }
            });
        }

        const seedBtn = document.getElementById("seedDemoBtn");
        if (seedBtn) {
            seedBtn.addEventListener("click", async function () {
                seedBtn.disabled = true;
                try {
                    const r = await fetch("/api/admin/seed", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ count: 25 })
                    });
                    const d = await r.json();
                    if (d.ok && d.payload) applyFullUpdate(d.payload);
                } finally {
                    seedBtn.disabled = false;
                }
            });
        }

        const clearDemoBtn = document.getElementById("clearDemoBtn");
        if (clearDemoBtn) {
            clearDemoBtn.addEventListener("click", async function () {
                clearDemoBtn.disabled = true;
                try {
                    const r = await fetch("/api/admin/clear-demo", { method: "POST" });
                    const d = await r.json();
                    if (d.ok && d.payload) applyFullUpdate(d.payload);
                } finally {
                    clearDemoBtn.disabled = false;
                }
            });
        }

        const resetAllBtn = document.getElementById("resetAllBtn");
        if (resetAllBtn) {
            resetAllBtn.addEventListener("click", async function () {
                if (!window.confirm("Delete ALL survey responses (both real and demo)?")) {
                    return;
                }
                resetAllBtn.disabled = true;
                try {
                    const r = await fetch("/api/admin/reset-all", { method: "POST" });
                    const d = await r.json();
                    if (d.ok && d.payload) applyFullUpdate(d.payload);
                } finally {
                    resetAllBtn.disabled = false;
                }
            });
        }

        const tbody = document.getElementById("responsesTableBody");
        if (tbody) {
            tbody.addEventListener("click", async function (e) {
                const btn = e.target.closest("[data-del-id]");
                if (!btn) return;
                const rowId = btn.getAttribute("data-del-id");
                const r = await fetch(`/api/admin/delete/${rowId}`, { method: "POST" });
                const d = await r.json();
                if (d.ok && d.payload) applyFullUpdate(d.payload);
            });
        }
    });
})();
