// 集群视图：集群级利用率时序 + 各机迷你卡阵 + 系统指标 + 集群内使用人 Top。
window.Views = window.Views || {};
window.Views.cluster = (function () {
  const { el, gpuCard, gpuPlaceholder, fmtPct, fmtGB, lineChart, barChart, Palette, badgeRow } = UI;

  // 该集群在其算力域内的局部索引与域内集群数 → 用于取一致的身份色
  function clusterColorFor(ov, c) {
    const gk = c.capacity_group || "";
    const inGroup = ov.clusters.filter((x) => (x.capacity_group || "") === gk);
    const ci = inGroup.findIndex((x) => x.key === c.key);
    return { color: Palette.clusterColor(gk, ci < 0 ? 0 : ci, inGroup.length || 1), groupKey: gk };
  }

  async function render(root, params) {
    const w = GM.state.window;
    const ov = await API.overview(w);
    const idx = ov.clusters.findIndex((c) => c.key === params.key);
    const c = ov.clusters[idx];
    if (!c) { root.innerHTML = `<p class='note'>${I18n.t('cluster_not_found')}</p>`; return; }
    const accent = clusterColorFor(ov, c).color;
    GM.crumb(`${I18n.t('overview')} › ${c.name}`);
    root.innerHTML = "";
    root.appendChild(el("span", { class: "back", onclick: () => GM.go("/") }, [I18n.t('back_to_overview')]));

    // 各主机一行迷你卡 + 系统
    const hostsPanel = el("div", { class: "panel", style: `border-left:5px solid ${accent}` },
      [el("h3", { class: "panel-head" }, [el("span", {}, [c.name + " · " + I18n.t('cluster_hosts_title')]), badgeRow(c)].filter(Boolean))]);
    if (c.note) hostsPanel.appendChild(el("div", { class: "note" }, [I18n.localize(c.note_i18n ?? c.note)]));
    c.hosts.forEach((h) => {
      const sys = h.system;
      const sysText = h.status === "planned"
        ? I18n.t('host_planned_info', { gpu_model: (h.meta && h.meta.gpu_model) || "GPU", count: h.gpu_count })
        : sys ? I18n.t('host_system_info', { cpu: fmtPct(sys.cpu_util_pct), load: sys.load1 ?? "—", mem_used: fmtGB(sys.mem_used_mib), mem_total: fmtGB(sys.mem_total_mib) }) : I18n.t('no_system_data');
      const statusText = h.status === "planned" ? I18n.t('planned') : (h.online ? I18n.t('online') : I18n.t('offline'));
      const name = el("div", { class: "host-name", onclick: () => GM.go(`/host/${h.key}`) },
        [el("div", { class: "hn" }, [h.display_name]), el("div", { class: "hs" }, [statusText])]);
      const offline = h.status !== "planned" && !h.online;
      const cards = el("div", { class: "cards" },
        h.gpus.length
          ? h.gpus.map((g) => gpuCard(g, { offline, onClick: (x) => GM.go(`/gpu/${x.gpu_id}`) }))
          : Array.from({ length: h.gpu_count || 0 }, (_, i) => gpuPlaceholder(i, h.display_name)));
      hostsPanel.appendChild(el("div", { class: "host-row" }, [name, el("div", { class: "host-sys" }, [sysText]), cards]));
    });
    root.appendChild(hostsPanel);

    // 集群级利用率时序
    if (!c.id || c.status === "planned") {
      root.appendChild(el("div", { class: "panel" }, [
        el("h3", {}, [I18n.t('cluster_access_status')]),
        el("div", { class: "note" }, [I18n.t('cluster_planned_note')]),
      ]));
      return;
    }
    const chartPanel = el("div", { class: "panel" }, [el("h3", {}, [I18n.t('cluster_avg_util', { window: w })])]);
    const chartDom = el("div", { class: "chart" });
    chartPanel.appendChild(chartDom);
    root.appendChild(chartPanel);
    const ser = await API.series("cluster", c.id, "util_gpu", w);
    const chart = lineChart(chartDom, [{ name: c.name, points: ser.points, color: accent }], { max: 100 });
    chart.resize();  // 修复超宽屏初始化时尺寸计算错误
    GM.onResize(chart);

    // 集群内使用人 Top（按本集群过滤）
    await usersPanel(root, w, c.key, c.name, accent);
  }

  async function usersPanel(root, w, clusterKey, clusterName, color) {
    const data = await API.usersTop(w, "gpu_hours", 10, clusterKey);
    const panel = el("div", { class: "panel" }, [el("h3", {}, [I18n.t('cluster_top_users', { name: clusterName, window: w })])]);
    const dom = el("div", { class: "chart", style: "height:260px" });
    panel.appendChild(dom); root.appendChild(panel);
    const labels = data.items.map((x) => x.username);
    const vals = data.items.map((x) => x.gpu_hours);
    const chart = barChart(dom, labels, vals, { xName: I18n.t('gpu_hours'), color: color || "#76b900" });
    chart.resize();  // 修复超宽屏初始化时尺寸计算错误
    GM.onResize(chart);
  }

  return { render };
})();
