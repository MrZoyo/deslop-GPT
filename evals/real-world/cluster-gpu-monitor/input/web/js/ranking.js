// 用户占用排行：同用户名跨设备聚合。明细按算力域→集群分组，
// 配色按算力域分色系（色带由 inventory 的 capacity_groups[].palette 指定），同集群内用相近色（拉明度）。
window.Views = window.Views || {};
window.Views.ranking = (function () {
  const { el, escapeHtml, Palette } = UI;

  // 依 topology 生成有序机器列 + 每台机器颜色 + 算力域分组信息。
  // 配色统一走 UI.Palette（与总览/cluster 页同一套家族色逻辑）。
  function buildLayout(topo, machines) {
    const present = new Set(machines.map((m) => m.key));
    const nameByKey = {};
    machines.forEach((m) => { nameByKey[m.key] = m.name; });
    const groups = [];
    const gmap = {};
    (topo.clusters || []).forEach((c) => {
      const gk = c.capacity_group || "";
      let g = gmap[gk];
      if (!g) {
        g = gmap[gk] = { key: gk, name: c.capacity_group_name || gk,
          sort: c.capacity_group_sort == null ? 99 : c.capacity_group_sort, clusters: [] };
        groups.push(g);
      }
      const hosts = (c.hosts || []).filter((h) => present.has(h.key));
      if (hosts.length) g.clusters.push({ key: c.key, name: c.name, hosts });
    });
    groups.sort((a, b) => a.sort - b.sort);

    const order = [];             // 有序机器列
    const groupColor = {};        // groupKey -> {color, tint}
    groups.forEach((g) => {
      groupColor[g.key] = { color: Palette.groupAccent(g.key), tint: Palette.groupTint(g.key) };
      const nC = g.clusters.length;
      g.clusters.forEach((c, ci) => {
        const nH = c.hosts.length;
        const clusterColor = Palette.clusterColor(g.key, ci, nC);
        c.hosts.forEach((h, hi) => {
          order.push({
            key: h.key, name: nameByKey[h.key] || h.display_name || h.key,
            color: Palette.machineColor(g.key, ci, nC, hi, nH),
            groupKey: g.key, groupName: g.name,
            // 折叠成"一列一集群"时要用集群名与集群身份色，故一并带上
            clusterKey: c.key, clusterName: c.name, clusterColor,
            firstInGroup: ci === 0 && hi === 0,
            firstInCluster: ci !== 0 && hi === 0,
          });
        });
      });
    });
    // topology 缺失的机器（防御）补末尾。正常情况下不会走到——后端已按 inventory
    // 过滤掉退役机器；这里只兜"DB 有、清单已删"的极端情况。
    machines.forEach((m) => {
      if (order.some((o) => o.key === m.key)) return;
      order.push({ key: m.key, name: m.name, color: Palette.groupAccent("_other"),
        groupKey: "_other", groupName: I18n.t('ranking_other'), clusterKey: "_other",
        clusterName: I18n.t('ranking_other'), clusterColor: Palette.groupAccent("_other"),
        firstInGroup: false, firstInCluster: false });
      groupColor._other = groupColor._other || { color: Palette.groupAccent("_other"), tint: Palette.groupTint("_other") };
    });
    // 表头算力域跨列
    const groupSpans = [];
    order.forEach((o) => {
      const last = groupSpans[groupSpans.length - 1];
      if (last && last.key === o.groupKey) last.span++;
      else groupSpans.push({ key: o.groupKey, name: o.groupName, span: 1, ...groupColor[o.groupKey] });
    });
    return { order, groupSpans, groupColor };
  }

  async function render(root) {
    const w = GM.state.window;
    GM.crumb(I18n.t('ranking_title'));
    const [data, topo] = await Promise.all([API.usersRanking(w), API.topology()]);
    root.innerHTML = "";
    root.appendChild(el("span", { class: "back", onclick: () => GM.go("/") }, [I18n.t('back_to_overview')]));

    if (!data.users.length) {
      root.appendChild(el("div", { class: "panel" },
        [el("div", { class: "note" }, [I18n.t('ranking_no_data', { window: w })])]));
      return;
    }

    if (data.truncated) {
      root.appendChild(el("div", { class: "note" }, [I18n.t('ranking_truncated', {
        shown: data.returned_users,
        total: data.total_users,
      })]));
    }

    const layout = buildLayout(topo, data.machines);
    const chartDom = el("div", { class: "chart" });
    root.appendChild(el("div", { class: "panel" }, [
      el("h3", {}, [I18n.t('ranking_chart_title', { window: w })]),
      el("div", { class: "note" }, [I18n.t('ranking_note')]),
      chartDom,
    ]));
    root.appendChild(table(data, layout));
    drawChart(chartDom, data, layout);
  }

  // 堆叠条 tooltip。默认的 trigger:"axis" 会把每台机器都列一行——32 台机器时
  // 变成 32 行（其中大半是 0），高过屏幕。这里只留有占用的机器、降序、最多 10 行，
  // 其余折成一行合计。
  const TOOLTIP_ROWS = 10;
  const TOOLTIP_COLOR = /^(?:#[0-9a-f]{3,8}|(?:rgb|hsl)a?\([\d\s.,%+-]+\))$/i;

  function rankTooltip(params) {
    if (!params || !params.length) return "";
    const items = params
      .filter((p) => (p.value && p.value.value != null ? p.value.value : p.value) > 0)
      .map((p) => ({
        name: p.seriesName,
        v: p.value && p.value.value != null ? p.value.value : p.value,
        color: p.color,
      }))
      .sort((a, b) => b.v - a.v);
    const total = items.reduce((a, x) => a + x.v, 0);
    const label = escapeHtml(params[0].axisValueLabel || params[0].name);
    const unit = escapeHtml(I18n.t('ranking_gpu_hours'));
    const head = `<b>${label}</b>` +
      `<span style="float:right;margin-left:16px">${total.toFixed(1)} ${unit}</span>`;
    if (!items.length) return head + "<br/>" + escapeHtml(I18n.t('ranking_no_usage'));

    const dot = (color) => {
      const safeColor = TOOLTIP_COLOR.test(String(color || "")) ? String(color) : "currentColor";
      return `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${safeColor};margin-right:6px"></span>`;
    };
    const rows = items.slice(0, TOOLTIP_ROWS).map((x) =>
      `${dot(x.color)}${escapeHtml(x.name)}<span style="float:right;margin-left:16px">${x.v.toFixed(1)}</span>`);
    const rest = items.slice(TOOLTIP_ROWS);
    if (rest.length) {
      const sum = rest.reduce((a, x) => a + x.v, 0);
      rows.push(`<span style="opacity:.7">${escapeHtml(I18n.t('ranking_others_sum', { n: rest.length }))}` +
        `<span style="float:right;margin-left:16px">${sum.toFixed(1)}</span></span>`);
    }
    return head + "<br/>" + rows.join("<br/>");
  }

  function drawChart(dom, data, layout) {
    const users = data.users;
    dom.style.height = Math.max(240, users.length * 30 + 90) + "px";
    const cs = getComputedStyle(document.body);
    const cv = (n, f) => (cs.getPropertyValue(n).trim() || f);
    const cText = cv("--chart-text", "#93a0b4"), cSplit = cv("--chart-split", "#212836");
    const cAxis = cv("--chart-axis", "#3a4453"), cInk = cv("--ink", "#eef2f8");
    const chart = echarts.init(dom);
    const usernames = users.map((u) => u.username);
    // 段间 1px 分隔：机器多了以后相邻色块（同集群只差明度）会连成一片，看不出边界。
    // 描边取面板底色而不是固定白/黑，日夜主题下都是"缝隙"而非"白线"。
    //
    // 但**极窄的段不能描边**：ECharts 的 border 画在矩形内侧，段宽只有 1~2px 时
    // 左右各 1px 的描边会把颜色吃光，看起来变成一条底色缝——反而更糊。
    // 这里按"该段占最长行的比例"估算像素宽度，低于阈值就不描边。
    const gap = cv("--panel-bg", "#0f1218");
    const maxTotal = Math.max(...users.map((u) => u.total || 0), 1);
    const THIN = 0.006;      // ≈ 800px 绘图区里的 5px
    const series = layout.order.map((m) => ({
      name: m.name, type: "bar", stack: "total", barMaxWidth: 26,
      emphasis: { focus: "series" },
      itemStyle: { color: m.color, borderColor: gap, borderWidth: 1 },
      data: users.map((u) => {
        const v = u.by_machine[m.key] || 0;
        if (v > 0 && v / maxTotal < THIN) {
          return { value: v, itemStyle: { color: m.color, borderWidth: 0 } };
        }
        return v;
      }),
    }));
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" },
        backgroundColor: cv("--tooltip-bg", "#141924"), borderColor: cv("--tooltip-border", "#2c3543"),
        textStyle: { color: cInk },
        confine: true,                  // 大集群下别把 tooltip 顶出屏幕
        formatter: rankTooltip },
      legend: { type: "scroll", top: 0, textStyle: { color: cText }, pageTextStyle: { color: cText } },
      grid: { left: 150, right: 30, top: 38, bottom: 30 },
      xAxis: { type: "value", name: I18n.t('ranking_gpu_hours'), nameTextStyle: { color: cText },
        axisLabel: { color: cText }, splitLine: { lineStyle: { color: cSplit } } },
      yAxis: { type: "category", data: usernames, inverse: true,
        axisLabel: { color: cText }, axisLine: { lineStyle: { color: cAxis } } },
      series,
    });
    chart.resize();  // 修复超宽屏初始化时尺寸计算错误
    GM.onResize(chart);
  }

  // 机器数超过这个值时，明细表默认按集群聚合成一列一集群。
  // 理由：32 台机器 = 35 列，横向必然溢出，而且大部分格子是"—"，信息密度极低。
  // 按集群聚合后 256 卡的机房也就 4~8 列，仍能一眼看出算力域分布。
  const COLLAPSE_OVER = 12;
  const LS_KEY = "gpumon.rank.expand";

  function wantExpanded(nMachines) {
    const saved = localStorage.getItem(LS_KEY);
    if (saved === "1") return true;
    if (saved === "0") return false;
    return nMachines <= COLLAPSE_OVER;      // 未选择过 → 按规模自动决定
  }

  // 把"机器列"折叠成"集群列"：同集群各机的 GPU·h 相加。
  function collapseToClusters(order) {
    const cols = [];
    const seen = {};
    order.forEach((m) => {
      let c = seen[m.clusterKey];
      if (!c) {
        c = seen[m.clusterKey] = {
          key: m.clusterKey, name: m.clusterName || m.clusterKey,
          color: m.clusterColor || m.color,
          groupKey: m.groupKey, groupName: m.groupName,
          hostKeys: [], firstInGroup: false,
        };
        cols.push(c);
      }
      c.hostKeys.push(m.key);
    });
    // 每个算力域的第一列打分隔线
    const firstOfGroup = {};
    cols.forEach((c) => {
      if (!firstOfGroup[c.groupKey]) {
        firstOfGroup[c.groupKey] = true;
        c.firstInGroup = true;
      }
    });
    return cols;
  }

  function table(data, layout) {
    const nM = layout.order.length;
    let expanded = wantExpanded(nM);

    const panel = el("div", { class: "panel compare-panel" });
    const render = () => {
      panel.innerHTML = "";
      const cols = expanded
        ? layout.order.map((m) => ({ ...m, hostKeys: [m.key] }))
        : collapseToClusters(layout.order);

      // 算力域跨列表头（按当前列集重算，展开/折叠都对得上）
      const spans = [];
      cols.forEach((c) => {
        const last = spans[spans.length - 1];
        if (last && last.key === c.groupKey) last.span++;
        else spans.push({ key: c.groupKey, name: c.groupName, span: 1,
          color: layout.groupColor?.[c.groupKey]?.color || c.color,
          tint: layout.groupColor?.[c.groupKey]?.tint });
      });

      const groupTier = el("tr", { class: "rank-group-row" }, [
        el("th", { class: "rank-corner", colspan: "3" }, []),
        ...spans.map((g) => el("th", {
          class: "rank-group-th", colspan: String(g.span),
          style: `--gc:${g.color};--gt:${g.tint || "transparent"}`,
        }, [g.name])),
      ]);
      const head = el("tr", {}, [
        el("th", { class: "rank-sticky rank-sticky-1" }, [I18n.t('ranking_rank')]),
        el("th", { class: "rank-sticky rank-sticky-2" }, [I18n.t('ranking_user')]),
        el("th", { class: "num rank-sticky rank-sticky-3" }, [I18n.t('ranking_total')]),
        ...cols.map((c) => el("th", {
          class: "num rank-machine-th" + (c.firstInGroup ? " grp-start" : ""),
          style: `--mc:${c.color}`,
          title: expanded ? c.groupName : `${c.groupName} · ${c.hostKeys.length} ${I18n.getLocale() === 'zh' ? '台' : 'hosts'}`,
        }, [el("span", { class: "rank-sw", style: `background:${c.color}` }), c.name])),
      ]);
      const rows = [groupTier, head];
      data.users.forEach((u, i) => rows.push(el("tr", {}, [
        el("td", { class: "rank-sticky rank-sticky-1" }, [String(i + 1)]),
        el("td", { class: "rank-sticky rank-sticky-2" }, [u.username]),
        el("td", { class: "num rank-total rank-sticky rank-sticky-3" }, [String(u.total)]),
        ...cols.map((c) => {
          const v = c.hostKeys.reduce((a, k) => a + (u.by_machine[k] || 0), 0);
          return el("td", { class: "num" + (c.firstInGroup ? " grp-start" : "") },
            [v > 0 ? String(Math.round(v * 10) / 10) : "—"]);
        }),
      ])));

      const toggle = el("button", {
        class: "rank-toggle",
        onclick: () => {
          expanded = !expanded;
          localStorage.setItem(LS_KEY, expanded ? "1" : "0");
          render();
        },
      }, [expanded ? I18n.t('ranking_collapse', { n: nM }) : I18n.t('ranking_expand', { n: nM })]);

      panel.appendChild(el("h3", { class: "panel-head" }, [
        el("span", {}, [expanded
          ? I18n.t('ranking_detail_expanded')
          : I18n.t('ranking_detail_collapsed')]),
        toggle,
      ]));
      if (!expanded) {
        panel.appendChild(el("div", { class: "note" }, [I18n.t('ranking_collapsed_note', { n: nM })]));
      }
      panel.appendChild(el("div", { class: "rank-scroll" }, [
        el("table", { class: "rank-table" }, [el("tbody", {}, rows)]),
      ]));
    };
    render();
    return panel;
  }

  return { render };
})();
