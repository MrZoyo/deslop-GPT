// 单卡视图：瞬时 KPI + 各窗均值小结 + 多指标时序（可切换）+ 当前使用人。
window.Views = window.Views || {};
window.Views.gpu = (function () {
  const { el, fmtPct, fmtGB, lineChart, utilCell } = UI;
  const METRICS = [
    { key: "util_gpu", label_key: "gpu_metric_util", yName: "%", max: 100, color: "#2563eb" },
    { key: "util_mem", label_key: "gpu_metric_mem_util", yName: "%", max: 100, color: "#0891b2" },
    { key: "mem_used", label_key: "gpu_metric_mem_used", yName: "MiB", color: "#7c3aed" },
    { key: "temp", label_key: "gpu_metric_temp", yName: "℃", color: "#dc2626" },
    { key: "power", label_key: "gpu_metric_power", yName: "W", color: "#d97706" },
  ];

  function findGpu(ov, id) {
    for (const c of ov.clusters)
      for (const h of c.hosts) {
        const g = h.gpus.find((x) => String(x.gpu_id) === String(id));
        if (g) return { g, h, c };
      }
    return null;
  }

  async function render(root, params) {
    const w = GM.state.window;
    const [ov, multi] = await Promise.all([API.overview(w), API.avgMulti("gpu", "util_gpu")]);
    const found = findGpu(ov, params.id);
    if (!found) { root.innerHTML = `<p class='note'>${I18n.t('gpu_not_found')}</p>`; return; }
    const { g, h, c } = found;
    GM.crumb(`${I18n.t('overview')} › ${c.name} › ${h.display_name} › GPU #${g.index}`);
    root.innerHTML = "";
    root.appendChild(el("span", { class: "back", onclick: () => GM.go(`/host/${h.key}`) }, [I18n.t('back_to', { name: h.display_name })]));

    const n = g.now || {};
    const kpi = [
      [I18n.t('gpu_instant_util'), fmtPct(n.util_gpu)],
      [I18n.t('gpu_memory'), `${fmtGB(n.mem_used_mib)} / ${fmtGB(g.mem_total_mib)}`],
      [I18n.t('gpu_temperature'), n.temp_c != null ? n.temp_c + "℃" : "—"],
      [I18n.t('gpu_power'), n.power_w != null ? Math.round(n.power_w) + "W" : "—"],
    ];
    root.appendChild(el("div", { class: "kpis" }, kpi.map(([k, v]) =>
      el("div", { class: "kpi" }, [el("div", { class: "v" }, [String(v)]), el("div", { class: "k" }, [k])]))));

    // 各窗平均利用率小结
    const wins = GM.state.meta.windows;
    const head = el("tr", {}, wins.map((x) => el("th", {}, [x])));
    const cells = wins.map((x) => {
      const it = (multi.windows[x] || []).find((i) => String(i.gpu_id) === String(g.gpu_id));
      return utilCell(it ? it.avg : null, it ? it.coverage : null);
    });
    root.appendChild(el("div", { class: "panel" }, [el("h3", {}, [I18n.t('gpu_avg_util_windows')]),
      el("table", {}, [el("tbody", {}, [head, el("tr", {}, cells)])])]));

    // 指标切换 + 时序
    const chartPanel = el("div", { class: "panel" });
    const switcher = el("div", { class: "win-switch", style: "margin-bottom:10px" });
    const dom = el("div", { class: "chart" });
    chartPanel.appendChild(el("h3", {}, [I18n.t('gpu_series_title', { window: w })]));
    chartPanel.appendChild(switcher);
    chartPanel.appendChild(dom);
    root.appendChild(chartPanel);

    let chart = null;
    async function draw(m) {
      Array.from(switcher.children).forEach((b) => b.classList.toggle("active", b.dataset.k === m.key));
      const s = await API.series("gpu", g.gpu_id, m.key, w);
      if (chart) chart.dispose();
      chart = lineChart(dom, [{ name: I18n.t(m.label_key), points: s.points, color: m.color }],
        { max: m.max, yName: m.yName });
      chart.resize();  // 修复超宽屏初始化时尺寸计算错误
      GM.onResize(chart);
    }
    METRICS.forEach((m) => {
      const b = el("button", { "data-k": m.key, onclick: () => draw(m) }, [I18n.t(m.label_key)]);
      switcher.appendChild(b);
    });
    await draw(METRICS[0]);

    // 当前使用人
    const us = g.users || [];
    const userRows = [el("tr", {}, [el("th", {}, [I18n.t('table_user')]), el("th", {}, [I18n.t('table_process')]), el("th", {}, [I18n.t('table_memory')])])];
    us.forEach((u) => userRows.push(el("tr", {}, [
      el("td", {}, [u.username || "?"]),
      el("td", {}, [u.comm || "—"]),
      el("td", { class: "num" }, [fmtGB(u.mem_used_mib)]),
    ])));
    const usersBody = us.length
      ? el("table", {}, [el("tbody", {}, userRows)])
      : el("div", { class: "note" }, [I18n.t('gpu_idle')]);
    root.appendChild(el("div", { class: "panel" }, [el("h3", {}, [I18n.t('gpu_current_users')]), usersBody]));
  }

  return { render };
})();
