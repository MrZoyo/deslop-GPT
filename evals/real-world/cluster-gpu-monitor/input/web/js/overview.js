// 总览视图：算力域 → 集群 → 设备，默认展开，保留热力、排行和多窗口对比。
window.Views = window.Views || {};
window.Views.overview = (function () {
  const { el, gpuCard, gpuPlaceholder, utilCell, fmtPct, fmtGB, Palette, ago, badgeRow } = UI;

  function statsForClusters(clusters) {
    const hosts = clusters.flatMap((c) => c.hosts || []);
    const gpus = hosts.flatMap((h) => h.gpus || []);
    const expected = hosts.reduce((a, h) => a + (h.gpu_count || 0), 0);
    const activeHosts = hosts.filter((h) => h.status !== "planned");
    // 在用数与"当前均值"按近期(10min)平滑值算，与卡片大字/底色及后端 cards_busy 一致。
    const busy = gpus.filter((g) => g.util_recent != null && g.util_recent >= (GM.state.meta.busy_threshold || 10)).length;
    const utilVals = gpus.map((g) => g.util_recent).filter((v) => v != null);
    return {
      clusters: clusters.length,
      hosts: hosts.length,
      activeHosts: activeHosts.length,
      plannedHosts: hosts.length - activeHosts.length,
      expected,
      discovered: gpus.length,
      busy,
      avg: utilVals.length ? utilVals.reduce((a, v) => a + v, 0) / utilVals.length : null,
    };
  }

  function kpis(ov) {
    const s = ov.summary;
    const cardsExpected = s.cards_expected || s.cards_total;
    const items = [
      { k: I18n.t('instant_util'), v: fmtPct(s.util_now_avg) },
      { k: I18n.t('window_avg', {window: s.window}), v: s.util_avg == null ? I18n.t('accumulating') : fmtPct(s.util_avg) },
      { k: I18n.t('gpu_busy_discovered'), v: `${s.cards_busy} / ${s.cards_total}`, hint: I18n.t('coverage_hint', {discovered: s.cards_total, expected: cardsExpected}) },
      { k: I18n.t('online_hosts'), v: `${s.hosts_online} / ${s.hosts_total}` },
    ];
    if (s.hosts_planned > 0) items.push({ k: I18n.t('planned_hosts'), v: s.hosts_planned });
    return el("div", { class: "kpis" },
      items.map(({ k, v, hint }) => el("div", { class: "kpi" }, [
        el("div", { class: "v" }, [String(v)]),
        el("div", { class: "k" }, [k]),
        hint ? el("div", { class: "hint" }, [hint]) : null,
      ])));
  }

  function legend(ov) {
    const hasPlanned = ov.clusters.some((c) => c.status === "planned" ||
      c.hosts.some((h) => h.status === "planned"));
    // 利用率是 0→100 的连续量：用按范围比例分段的刻度尺表达"越往右越忙"。
    // 每段颜色取自 utilColor（档位内代表值），保证图例与卡片一致，也随主题联动。
    const bands = [
      { t: I18n.t('idle'), v: 5, from: 0, to: 10 },
      { t: I18n.t('in_use'), v: 20, from: 10, to: 40 },
      { t: I18n.t('idle'), v: 50, from: 40, to: 70 },  // 偏忙用 idle 键（未单独翻译）
      { t: I18n.t('active'), v: 80, from: 70, to: 90 },  // 繁忙用 active
      { t: I18n.t('idle'), v: 95, from: 90, to: 100 },  // 满载暂用 idle（未单独翻译）
    ];
    // 重新定义带原文的 bands
    const bandLabels = I18n.getLocale() === 'zh'
      ? [{ t: "空闲", v: 5, from: 0, to: 10 },
         { t: "在用", v: 20, from: 10, to: 40 },
         { t: "偏忙", v: 50, from: 40, to: 70 },
         { t: "繁忙", v: 80, from: 70, to: 90 },
         { t: "满载", v: 95, from: 90, to: 100 }]
      : [{ t: "Idle", v: 5, from: 0, to: 10 },
         { t: "In Use", v: 20, from: 10, to: 40 },
         { t: "Busy", v: 50, from: 40, to: 70 },
         { t: "Very Busy", v: 80, from: 70, to: 90 },
         { t: "Full", v: 95, from: 90, to: 100 }];
    const bar = el("div", { class: "util-scale-bar" },
      bandLabels.map((b) => {
        const { bg, dark } = UI.utilColor(b.v);
        return el("div", {
          class: "seg", style: `flex:${b.to - b.from};background:${bg};color:${dark ? "#0a0d14" : "#fff"}`,
          title: `${b.t} ${b.from}–${b.to}%`,
        }, [b.t]);
      }));
    const ticks = el("div", { class: "util-scale-ticks" },
      [0, 10, 40, 70, 90, 100].map((v) => el("span", { style: `left:${v}%` }, [String(v)])));
    const scale = el("div", { class: "util-scale" }, [bar, ticks]);
    const children = [el("span", { class: "legend-cap" }, [I18n.t('utilization_pct')]), scale];
    if (hasPlanned) {
      children.push(el("span", { class: "planned-legend" },
        [el("span", { class: "sw planned-sw" }), I18n.t('planned')]));
    }
    return el("div", { class: "legend util-legend" }, children);
  }

  function groupClusters(ov) {
    const groups = (ov.capacity_groups || GM.state.meta.capacity_groups || [])
      .map((g) => ({ ...g, clusters: [] }));
    const byKey = {};
    groups.forEach((g) => { byKey[g.key] = g; });
    ov.clusters.forEach((c) => {
      const key = c.capacity_group || "";
      if (!byKey[key]) {
        byKey[key] = { key, name: c.capacity_group_name || key || I18n.t('empty_state'),
          sort_order: 999, clusters: [] };
        groups.push(byKey[key]);
      }
      byKey[key].clusters.push(c);
    });
    return groups
      .filter((g) => g.clusters.length)
      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  }

  function capacityNav(groups) {
    return el("div", { class: "capacity-tabs" }, groups.map((g) => {
      const st = statsForClusters(g.clusters);
      return el("button", { onclick: () => document.getElementById("cap-" + g.key)?.scrollIntoView({ behavior: "smooth", block: "start" }) }, [
        el("span", { class: "tab-name" }, [g.name]),
        el("span", { class: "tab-meta" }, [I18n.t('cluster_index_machines', {n: st.clusters, m: st.expected})]),
      ]);
    }));
  }

  function alertPanel(ov) {
    const activeHosts = ov.clusters.flatMap((c) => c.hosts.map((h) => ({ ...h, cluster: c.name })))
      .filter((h) => h.status !== "planned");
    const offline = activeHosts.filter((h) => !h.online);
    const hot = ov.clusters.flatMap((c) => c.hosts.flatMap((h) => (h.gpus || []).map((g) => ({ g, h, c }))))
      .filter((x) => x.g.util_recent != null && x.g.util_recent >= 90)
      .sort((a, b) => b.g.util_recent - a.g.util_recent);
    const planned = ov.clusters.filter((c) => c.status === "planned" || c.hosts.some((h) => h.status === "planned"));
    const rows = [];
    rows.push(el("div", { class: offline.length ? "alert bad" : "alert ok" },
      [el("b", {}, [String(offline.length)]), el("span", {}, [I18n.t('offline_active_hosts')])]));
    rows.push(el("div", { class: hot.length ? "alert hot" : "alert ok" },
      [el("b", {}, [String(hot.length)]), el("span", {}, [I18n.t('full_load_gpus')])]));
    if (planned.length) {
      rows.push(el("div", { class: "alert planned-alert" },
        [el("b", {}, [String(planned.length)]), el("span", {}, [I18n.t('planned_clusters')])]));
    }
    return el("div", { class: "ops-strip", style: `--alert-count:${rows.length}` }, rows);
  }

  function hotGpuPanel(ov) {
    const items = ov.clusters.flatMap((c) => c.hosts.flatMap((h) =>
      (h.gpus || []).map((g) => ({ c, h, g }))))
      .filter((x) => x.g.util_recent != null)
      .sort((a, b) => b.g.util_recent - a.g.util_recent)
      .slice(0, 8);
    const rows = items.length ? items.map((x) => el("button", {
      onclick: () => GM.go(`/gpu/${x.g.gpu_id}`),
      title: `${x.c.name} / ${x.h.display_name} / GPU #${x.g.index}`,
    }, [
      el("span", { class: "hot-gpu-main" }, [`${x.h.display_name} #${x.g.index}`]),
      el("span", { class: "hot-gpu-util" }, [fmtPct(x.g.util_recent)]),
    ])) : [el("div", { class: "note" }, [I18n.t('no_realtime_data')])];
    return el("div", { class: "hot-gpus" }, rows);
  }

  function capacitySection(group, idx) {
    const st = statsForClusters(group.clusters);
    const nC = group.clusters.length;
    const section = el("section", { class: "capacity-section", id: "cap-" + group.key, style: `--caccent:${Palette.groupAccent(group.key)}` });
    section.appendChild(el("div", { class: "capacity-head" }, [
      el("div", { class: "capacity-title" }, [
        el("div", { class: "eyebrow" }, ["CAPACITY DOMAIN"]),
        el("h2", {}, [group.name]),
        badgeRow(group),
      ].filter(Boolean)),
      el("div", { class: "capacity-metrics" }, [
        metric(I18n.t('capacity_metrics_clusters'), st.clusters),
        metric(I18n.t('capacity_metrics_hosts'), `${st.activeHosts}/${st.hosts}`),
        metric(I18n.t('capacity_metrics_gpus'), `${st.discovered}/${st.expected}`),
        metric(I18n.t('capacity_metrics_avg'), fmtPct(st.avg)),
      ]),
    ]));
    const description = I18n.localize(group.description_i18n ?? group.description);
    if (description) section.appendChild(el("div", { class: "capacity-note" }, [description]));
    section.appendChild(el("div", { class: "cluster-tabs" },
      group.clusters.map((c, i) => clusterTab(c, i, group.key, nC))));
    group.clusters.forEach((c, i) => section.appendChild(clusterBlock(c, i, group.key, nC)));
    return section;
  }

  function metric(label, value) {
    return el("div", { class: "mini-metric" }, [
      el("span", {}, [label]),
      el("b", {}, [String(value)]),
    ]);
  }

  function clusterTab(c, idx, groupKey, nC) {
    const st = statsForClusters([c]);
    const col = Palette.clusterColor(groupKey || "", idx, nC || 1);
    return el("button", { onclick: () => document.getElementById("cluster-" + c.key)?.scrollIntoView({ behavior: "smooth", block: "start" }) }, [
      el("span", { class: "cluster-dot", style: `background:${col}` }),
      el("span", {}, [c.name]),
      el("small", {}, [I18n.t('cluster_index_machines', {n: st.hosts, m: st.expected})]),
    ]);
  }

  function clusterBlock(c, idx, groupKey, nC) {
    const st = statsForClusters([c]);
    const col = Palette.clusterColor(groupKey || "", idx, nC || 1);
    const details = el("details", { class: `cluster-block ${c.status === "planned" ? "planned-block" : ""}`, id: "cluster-" + c.key, open: "" });
    const nameLink = el("a", {
      class: "cluster-title-name",
      href: `#/cluster/${encodeURIComponent(c.key)}`,
      title: I18n.t('view_cluster_detail', {name: c.name}),
      onclick: (e) => {
        if (e.metaKey || e.ctrlKey || e.shiftKey) return;
        e.preventDefault();
        e.stopPropagation();
        GM.go(`/cluster/${c.key}`);
      },
    }, [c.name]);
    const summary = el("summary", { style: `--caccent:${col}` }, [
      el("div", { class: "cluster-title" }, [
        el("span", { class: "cluster-index" }, [String(idx + 1).padStart(2, "0")]),
        nameLink,
        badgeRow(c),
        c.status === "planned" ? el("span", { class: "badge planned-badge" }, [I18n.t('planned')]) : null,
      ].filter(Boolean)),
      el("div", { class: "cluster-stats" }, [
        metric(I18n.t('hosts'), st.hosts),
        metric("GPU", `${st.discovered}/${st.expected}`),
        metric(I18n.t('in_use'), st.busy),
        metric(I18n.t('avg'), fmtPct(st.avg)),
        el("span", { class: "cluster-toggle", title: I18n.t('expand_collapse') }, []),
      ]),
    ]);
    details.appendChild(summary);
    if (c.note) {
      const noteColor = `color-mix(in srgb, ${col} 65%, var(--bg))`;
      details.appendChild(el("div", { class: "cluster-note", style: `--note-accent:${noteColor}` }, [I18n.localize(c.note_i18n ?? c.note)]));
    }
    if (!c.hosts.length) {
      details.appendChild(el("div", { class: "empty-state" }, [I18n.t('no_devices')]));
    } else {
      c.hosts.forEach((h) => details.appendChild(hostRow(h, c)));
    }
    return details;
  }

  function hostRow(h, c) {
    const sys = h.system;
    const sysText = h.status === "planned"
      ? I18n.t('host_planned_info', {gpu_model: (h.meta && h.meta.gpu_model) || "GPU", count: h.gpu_count})
      : sys
        ? I18n.t('host_system_info', {cpu: fmtPct(sys.cpu_util_pct), load: sys.load1 ?? "-", mem_used: fmtGB(sys.mem_used_mib), mem_total: fmtGB(sys.mem_total_mib)})
        : I18n.t('no_system_data');
    const statusLabel = h.status === "planned" ? I18n.t('planned') : (h.online ? I18n.t('online') : I18n.t('offline_n_times', {n: h.consec_fail || 0}));
    const offline = h.status !== "planned" && !h.online;
    const cards = (h.gpus && h.gpus.length)
      ? h.gpus.map((g) => gpuCard(g, { offline, onClick: (x) => GM.go(`/gpu/${x.gpu_id}`) }))
      : Array.from({ length: h.gpu_count || 0 }, (_, i) => gpuPlaceholder(i, h.display_name));
    const row = el("div", { class: `host-row ${h.status === "planned" ? "planned-host" : ""}` }, [
      el("div", { class: "host-name", onclick: () => GM.go(`/host/${h.key}`) }, [
        el("div", { class: "hn" }, [h.display_name]),
        el("div", { class: "hs" }, [`${statusLabel} · ${I18n.t('cards_seen', {seen: h.gpus_seen ?? 0, expected: h.gpu_count})}`]),
      ]),
      el("div", { class: "host-sys" }, [sysText]),
      el("div", { class: "cards" }, cards),
    ]);
    if (h.last_error && h.status !== "planned") row.title = `${c.name}: ${h.last_error}`;
    if (h.note && h.status === "planned") row.title = I18n.localize(h.note_i18n ?? h.note);
    return row;
  }

  function compareTable(ov, multi) {
    const wins = GM.state.meta.windows;
    const byWin = {};
    wins.forEach((w) => {
      byWin[w] = {};
      (multi.windows[w] || []).forEach((it) => { byWin[w][it.host] = it; });
    });
    const head = el("tr", {}, [el("th", {}, [I18n.t('hosts')]), el("th", {}, [I18n.t('cluster_column')]), el("th", {}, [I18n.t('status')]),
      ...wins.map((w) => el("th", { class: "num" }, [w + " " + I18n.t('avg')]))]);
    const rows = [head];
    ov.clusters.forEach((c) => c.hosts.forEach((h) => {
      const tds = [
        el("td", {}, [el("a", { onclick: () => GM.go(`/host/${h.key}`), href: "javascript:;" }, [h.display_name])]),
        el("td", {}, [c.name]),
        el("td", {}, [h.status === "planned" ? I18n.t('planned') : (h.online ? I18n.t('online') : I18n.t('offline'))]),
      ];
      wins.forEach((w) => {
        const it = byWin[w][h.key];
        tds.push(utilCell(it ? it.avg : null, it ? it.coverage : null));
      });
      rows.push(el("tr", {}, tds));
    }));
    return el("div", { class: "panel compare-panel" }, [
      el("h3", {}, [I18n.t('compare_table_title')]),
      el("table", {}, [el("tbody", {}, rows)]),
    ]);
  }

  async function render(root) {
    const w = GM.state.window;
    GM.crumb(I18n.t('overview'));
    const [ov, multi] = await Promise.all([API.overview(w), API.avgMulti("host", "util_gpu")]);
    const groups = groupClusters(ov);
    root.innerHTML = "";
    root.appendChild(el("section", { class: "command-panel" }, [
      el("div", { class: "command-copy" }, [
        el("div", { class: "eyebrow" }, ["GPU FLEET CONTROL"]),
        el("h1", {}, [I18n.getLocale() === 'zh' ? "算力监控总览" : "GPU Fleet Overview"]),
        el("div", { class: "note" }, [I18n.t('updated_at', {time: ago(ov.now)}) + " · " + (I18n.getLocale() === 'zh' ? `每 ${GM.state.meta.poll_interval_s || 30} 秒刷新` : `Refresh every ${GM.state.meta.poll_interval_s || 30}s`)]),
      ]),
      el("div", {}, [alertPanel(ov), hotGpuPanel(ov)]),
    ]));
    root.appendChild(kpis(ov));
    root.appendChild(legend(ov));
    root.appendChild(capacityNav(groups));
    groups.forEach((g, i) => root.appendChild(capacitySection(g, i)));
    root.appendChild(compareTable(ov, multi));
  }

  return { render };
})();
