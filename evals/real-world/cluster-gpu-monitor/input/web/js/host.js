// 单机视图：系统指标 + 8 卡网格（瞬时/均值/使用人）+ 多卡利用率时序 + 该机使用人。
window.Views = window.Views || {};
window.Views.host = (function () {
  const { el, gpuCard, gpuPlaceholder, fmtPct, fmtGB, lineChart, Palette } = UI;

  async function render(root, params) {
    const w = GM.state.window;
    const ov = await API.overview(w);
    let host = null, cluster = null;
    for (const c of ov.clusters) {
      const h = c.hosts.find((x) => x.key === params.key);
      if (h) { host = h; cluster = c; break; }
    }
    if (!host) { root.innerHTML = `<p class='note'>${I18n.t('host_not_found')}</p>`; return; }
    GM.crumb(`${I18n.t('overview')} › ${cluster.name} › ${host.display_name}`);
    root.innerHTML = "";
    root.appendChild(el("span", { class: "back", onclick: () => GM.go(`/cluster/${cluster.key}`) }, [I18n.t('back_to', { name: cluster.name })]));

    // 系统指标 KPI
    const sys = host.system || {};
    const kpi = [
      [I18n.t('host_cpu_util'), fmtPct(sys.cpu_util_pct)],
      [I18n.t('host_load_cores'), `${sys.load1 ?? "—"} / ${sys.ncpu ?? "—"}`],
      [I18n.t('host_memory'), `${fmtGB(sys.mem_used_mib)} / ${fmtGB(sys.mem_total_mib)}`],
      [I18n.t('host_status'), host.status === "planned" ? I18n.t('planned') : (host.online ? I18n.t('online') : I18n.t('host_offline_n', { n: host.consec_fail }))],
    ];
    root.appendChild(el("div", { class: "kpis" }, kpi.map(([k, v]) =>
      el("div", { class: "kpi" }, [el("div", { class: "v" }, [String(v)]), el("div", { class: "k" }, [k])]))));
    if (host.last_error) root.appendChild(el("div", { class: "note" }, [I18n.t('host_last_error') + host.last_error]));

    // 8 卡网格
    const gridOffline = host.status !== "planned" && !host.online;
    const grid = el("div", { class: "panel" }, [el("h3", {}, [I18n.t('host_gpu_title')]),
      el("div", { class: "cards" }, host.gpus.length
        ? host.gpus.map((g) => gpuCard(g, { offline: gridOffline, onClick: (x) => GM.go(`/gpu/${x.gpu_id}`) }))
        : Array.from({ length: host.gpu_count || 0 }, (_, i) => gpuPlaceholder(i, host.display_name)))]);
    root.appendChild(grid);

    if (host.status === "planned" || !host.gpus.length) {
      root.appendChild(el("div", { class: "panel" }, [
        el("h3", {}, [I18n.t('cluster_access_status')]),
        el("div", { class: "note" }, [I18n.localize(host.note_i18n ?? host.note) || I18n.t('host_planned_note')]),
      ]));
      return;
    }

    // 多卡利用率时序（每卡一条线）
    const chartPanel = el("div", { class: "panel" }, [el("h3", {}, [I18n.t('host_gpu_util_chart', { window: w })])]);
    const dom = el("div", { class: "chart" });
    chartPanel.appendChild(dom); root.appendChild(chartPanel);
    const seriesData = await Promise.all(host.gpus.map((g) =>
      API.series("gpu", g.gpu_id, "util_gpu", w).then((s) => ({ name: "#" + g.index, points: s.points }))));
    // 同机多卡：唯一目标是把每条线区分开 → 色相分散、避开满载红（非分组相近色）
    const palette = Palette.seriesColors(seriesData.length);
    seriesData.forEach((s, i) => (s.color = palette[i]));
    const chart = lineChart(dom, seriesData, { max: 100 });
    chart.resize();  // 修复超宽屏初始化时尺寸计算错误
    GM.onResize(chart);

    // 当前使用人（该机）
    const users = [];
    host.gpus.forEach((g) => (g.users || []).forEach((u) =>
      users.push({ gpu: g.index, username: u.username, comm: u.comm, mem: u.mem_used_mib })));
    const rows = [el("tr", {}, [el("th", {}, [I18n.t('table_card')]), el("th", {}, [I18n.t('table_user')]), el("th", {}, [I18n.t('table_process')]), el("th", {}, [I18n.t('table_memory')])])];
    users.sort((a, b) => (b.mem || 0) - (a.mem || 0)).forEach((u) =>
      rows.push(el("tr", {}, [el("td", {}, ["#" + u.gpu]), el("td", {}, [u.username || "?"]),
        el("td", {}, [u.comm || "—"]), el("td", { class: "num" }, [fmtGB(u.mem)])])));
    root.appendChild(el("div", { class: "panel" }, [el("h3", {}, [I18n.t('host_current_users_title')]),
      users.length ? el("table", {}, [el("tbody", {}, rows)]) : el("div", { class: "note" }, [I18n.t('host_no_processes')])]));
  }

  return { render };
})();
