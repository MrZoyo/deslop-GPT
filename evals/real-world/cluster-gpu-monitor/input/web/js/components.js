// 通用渲染辅助：颜色映射、格式化、DOM、ECharts 主题。
window.UI = (function () {
  // 利用率 → 颜色（分段，一眼区分忙闲）。返回 {bg, dark} dark 表示用深色文字。
  function utilColor(v) {
    if (v == null) return { bg: null, dark: true };       // 无数据
    if (v >= 90) return { bg: "#e52020", dark: false };    // 红：满载
    if (v >= 70) return { bg: "#df6500", dark: false };    // 橙
    if (v >= 40) return { bg: "#ef9100", dark: true };     // 黄
    // 绿（在用）：酸绿 #76b900 在白底上对比不足，浅色模式换用更深的绿。
    if (v >= 10) {
      const light = !!(document.body && document.body.dataset.theme === "light");
      return { bg: light ? "#5c8a00" : "#76b900", dark: true };
    }
    return { bg: "#5e5e5e", dark: false };                 // 灰：空闲
  }
  const fmtPct = (v) => (v == null ? "—" : Math.round(v) + "%");
  const fmtGB = (mib) => (mib == null ? "—" : (mib / 1024).toFixed(0) + "G");
  const clusterVar = (i) => `var(--c${i % 6})`;

  function escapeHtml(value) {
    const escaped = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
    return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => escaped[char]);
  }

  // ── 全站配色体系 ─────────────────────────────────────────────
  // 两类颜色，目标不同、策略相反：
  //  1) 身份/归属色（Palette.*）：表达"这是哪个算力域/集群/机器"。
  //     同算力域用同一色系，域内各集群按色相分散，集群内各机拉明度。
  //     用于总览集群、cluster 页、ranking——一屏内多集群共存时便于归堆。
  //  2) 区分色（Palette.seriesColors）：表达"这是第几条线"，唯一目标是最大化区分。
  //     色相尽量分散，且避开满载红(#e52020)以免与利用率语义色混淆。
  //     用于同机多卡时序等"都属同一实体、只需分开"的场景。
  // utilColor（利用率语义色）与此无关，全站不变。
  const Palette = (function () {
    // 每条色带 = 一个算力域：h0→h1 色相区间 + 基准饱和/明度 + 机内明度步长。
    // 色带跨度要够宽，否则域内多集群落在同一片色里难以区分；中点是该色带的身份色。
    // 色带按名字索引，由后端 /api/meta 的 capacity_groups[].palette 指定（inventory 可写死，
    // 不写则按域的 sort_order 轮转分配）——这里不再出现任何机构名。
    const BANDS = {
      lime:   { h0: 72,  h1: 200, s: 62, l: 47, step: 9 },   // 莱姆黄绿 → 纯绿 → 青蓝
      violet: { h0: 322, h1: 258, s: 56, l: 57, step: 11 },  // 品红 → 紫罗兰
      azure:  { h0: 188, h1: 232, s: 60, l: 52, step: 10 },  // 青 → 宝蓝
      amber:  { h0: 45,  h1: 22,  s: 68, l: 50, step: 9 },   // 琥珀金 → 赭橙（避开满载红）
      rose:   { h0: 350, h1: 315, s: 55, l: 56, step: 10 },  // 玫红 → 紫红
      teal:   { h0: 168, h1: 196, s: 52, l: 44, step: 9 },   // 松绿 → 青
      indigo: { h0: 252, h1: 224, s: 50, l: 58, step: 11 },  // 靛蓝 → 群青
      slate:  { h0: 210, h1: 240, s: 16, l: 55, step: 10 },  // 中性灰蓝（兜底/未分组）
    };
    const FALLBACK = BANDS.slate;
    // 域 key → 色带名，由 setGroups() 从后端元数据填充
    let bandOf = {};
    // 内置色带用尽后按黄金角生成新色相，保证第 9 个及以后的域也各不相同、不撞灰
    const GOLDEN = 137.508;
    const generated = {};
    function genBand(key, i) {
      if (!generated[key]) {
        const h = (18 + GOLDEN * (i + 1)) % 360;
        generated[key] = { h0: h, h1: (h + 38) % 360, s: 54, l: 52, step: 10 };
      }
      return generated[key];
    }
    const hsl = (h, s, l) => `hsl(${Math.round(h)}, ${Math.round(s)}%, ${Math.round(l)}%)`;
    const hsla = (h, s, l, a) => `hsla(${Math.round(h)}, ${Math.round(s)}%, ${Math.round(l)}%, ${a})`;
    // 浅色模式：身份色统一压暗，保证在白底上的对比（深色模式保持原亮度不变）。
    const isLight = () => !!(document.body && document.body.dataset.theme === "light");
    const L = (l) => (isLight() ? Math.max(28, l - 13) : l);

    // 域 key → 色带。优先用后端指定的色带名；没有映射时按域出现顺序生成，绝不落回灰色。
    function band(groupKey) {
      const named = bandOf[groupKey];
      if (named && BANDS[named]) return BANDS[named];
      if (groupKey == null || groupKey === "") return FALLBACK;
      const idx = Object.keys(bandOf).indexOf(groupKey);
      return genBand(groupKey, idx < 0 ? Object.keys(generated).length : idx);
    }

    // 由 app.js 在拿到 /api/meta 后调用：记录每个算力域用哪条色带
    function setGroups(groups) {
      bandOf = {};
      (groups || []).forEach((g) => { if (g && g.key) bandOf[g.key] = g.palette; });
    }

    // 集群在域内的色相：单集群取色带中点，多集群沿色带铺开
    const clusterHue = (b, ci, nC) => (nC <= 1 ? (b.h0 + b.h1) / 2 : b.h0 + (b.h1 - b.h0) * (ci / (nC - 1)));

    return {
      band,
      setGroups,
      // 算力域代表色（分组表头/eyebrow）：色带中点
      groupAccent(groupKey) {
        const b = band(groupKey);
        return hsl((b.h0 + b.h1) / 2, b.s, L(b.l));
      },
      groupTint(groupKey, a) {
        const b = band(groupKey);
        return hsla((b.h0 + b.h1) / 2, b.s, L(b.l), a == null ? 0.16 : a);
      },
      // 集群身份色（总览左边框/圆点、cluster 页）
      clusterColor(groupKey, ci, nC) {
        const b = band(groupKey);
        return hsl(clusterHue(b, ci, nC || 1), b.s, L(b.l));
      },
      // 机器色（ranking 堆叠条 / 明细表）：集群色相 + 机内明度偏移
      machineColor(groupKey, ci, nC, hi, nH) {
        const b = band(groupKey);
        const lOff = nH <= 1 ? 0 : (hi - (nH - 1) / 2) * b.step;
        return hsl(clusterHue(b, ci, nC || 1), b.s, L(b.l + lOff));
      },
      // n 条分散区分色：色相环等分（起点避开红），跳过满载红附近色相
      seriesColors(n) {
        const out = [];
        const start = 145;            // 从绿松起步，远离满载红
        for (let i = 0; i < n; i++) {
          let h = (start + (360 / Math.max(1, n)) * i) % 360;
          if (h > 5 && h < 20) h = 28; // 躲开纯红(#e52020≈0°)相邻区
          // 明度轻微交替，进一步拉开相邻线
          const l = 58 + (i % 2 ? -6 : 6);
          out.push(hsl(h, 62, L(l)));
        }
        return out;
      },
    };
  })();

  function cssVar(name, fallback) {
    const v = getComputedStyle(document.body).getPropertyValue(name).trim();
    return v || fallback;
  }

  function chartTheme() {
    return {
      tooltipBg: cssVar("--tooltip-bg", "#111111"),
      tooltipBorder: cssVar("--tooltip-border", "#2f2f2f"),
      text: cssVar("--chart-text", "#a7a7a7"),
      split: cssVar("--chart-split", "#262626"),
      axis: cssVar("--chart-axis", "#5e5e5e"),
      bar: cssVar("--accent", "#76b900"),
    };
  }

  function el(tag, attrs, children) {
    const e = document.createElement(tag);
    if (attrs) for (const k in attrs) {
      if (k === "class") e.className = attrs[k];
      else if (k === "style") e.style.cssText = attrs[k];
      else if (k.startsWith("on")) e.addEventListener(k.slice(2), attrs[k]);
      else if (attrs[k] != null) e.setAttribute(k, attrs[k]);
    }
    (children || []).forEach((c) => {
      if (c == null) return;
      if (typeof c === "string" || typeof c === "number")
        e.appendChild(document.createTextNode(String(c)));
      else e.appendChild(c);
    });
    return e;
  }

  // 一个 GPU 状态块：深色底承载结构，利用率只用细状态条表达，避免大面积高饱和色。
  // GPU 占用状态：'idle'=无人，'held'=占着显存但 GPU 空闲（空占），'active'=在用。
  // 使用人已由后端过滤掉未占显存的进程；util<5% 视为空闲（含采样噪声）。
  function usageState(g) {
    const hasUser = (g.users || []).length > 0;
    if (!hasUser) return "idle";
    // 用近期(10min)平滑值判空占，与卡片大字一致：任务停后即算空占，训练间隙的瞬时 0 不误判。
    const util = g.util_recent != null ? g.util_recent : null;
    return (util != null && util < 5) ? "held" : "active";
  }

  function gpuCard(g, opts) {
    opts = opts || {};
    // 大字/底色显示近期(10min)平均利用率（含"连续空闲即置零"），抹平瞬时抖动；瞬时值仅留在 tooltip。
    const util = g.util_recent != null ? g.util_recent : null;
    const { bg } = utilColor(util);
    const pct = util == null ? 0 : Math.max(0, Math.min(100, Math.round(util)));
    // 离线：主机断连，实时值已陈旧（后端已置空 now）。显示"离线"而非"—"，与从未采到的 nodata 区分。
    const offline = !!opts.offline;
    // 空占：占着显存但 GPU 空闲。低调标记，与"完全没人用"区分。
    const held = !offline && usageState(g) === "held";
    const cls = "card" + (bg == null ? " nodata" : "") +
      (offline ? " offline" : "") + (held ? " held" : "");
    const nowText = offline ? I18n.t('offline') : (util == null ? "—" : Math.round(util));
    // 满载 100 是利用率唯一的 3 位数，18px 下会撞上左上角 #index 与右上角状态点 → 收窄一档。
    const nowCls = "now" + (String(nowText).length >= 3 ? " now-wide" : "");
    const node = el("div", {
      class: cls,
      style: bg ? `--util-color:${bg};--util-pct:${pct}%` : "",
      title: offline ? I18n.t('gpu_offline', {index: g.index, name: g.name ? " " + g.name : ""}) : tooltipFor(g),
      onclick: () => opts.onClick && opts.onClick(g),
    }, [
      el("span", { class: "idx" }, ["#" + g.index]),
      el("span", { class: nowCls }, [nowText]),
      held ? el("span", { class: "held-mark", title: I18n.t('held_tooltip') }, []) : (bg ? el("span", { class: "signal" }) : null),
      !offline && g.avg != null ? el("span", { class: "avg" }, [I18n.t('avg') + " " + Math.round(g.avg)]) : null,
    ]);
    return node;
  }

  function gpuPlaceholder(index, label) {
    return el("div", {
      class: "card planned",
      title: `${label || I18n.t('planned_gpu')} #${index}`,
    }, [
      el("span", { class: "idx" }, ["#" + index]),
      el("span", { class: "now" }, ["--"]),
      el("span", { class: "avg" }, [I18n.t('planned')]),
    ]);
  }

  // 一卡上最多列几个使用人。共享卡（尤其推理机）可能有十几个进程，
  // 全列出来 title 会长到盖住半屏。
  const MAX_TOOLTIP_USERS = 8;

  function tooltipFor(g) {
    const n = g.now || {};
    // 占显存的进程 ps 可能解析不到用户名（进程刚退出/无权限），显示"未知"而非留空；去重避免多个"未知"重复。
    const uniq = [...new Set((g.users || []).map((u) => u.username || I18n.t('unknown_user')))];
    const names = uniq.slice(0, MAX_TOOLTIP_USERS).join(", ") +
      (uniq.length > MAX_TOOLTIP_USERS ? ` ${I18n.t('and_n_more', {n: uniq.length})}` : "");
    const state = usageState(g);
    const usageLine = state === "idle" ? I18n.t('usage_idle')
      : (state === "held" ? I18n.t('usage_held', {names}) : I18n.t('usage_active', {names}));
    return [
      `GPU #${g.index} ${g.name || ""}`,
      `${I18n.t('recent_util_10min')}: ${fmtPct(g.util_recent)}`,
      `${I18n.t('instant_util_short')}: ${fmtPct(n.util_gpu)}`,
      g.avg != null ? `${I18n.t('window_avg_short')}: ${Math.round(g.avg)}% (${I18n.t('coverage', {pct: Math.round((g.coverage || 0) * 100)})})` : `${I18n.t('window_avg_short')}: ${I18n.t('data_accumulating')}`,
      `${I18n.t('memory')}: ${fmtGB(n.mem_used_mib)}/${fmtGB(g.mem_total_mib)}`,
      n.temp_c != null ? `${I18n.t('temperature')}: ${n.temp_c}℃  ${I18n.t('power')}: ${n.power_w != null ? Math.round(n.power_w) + "W" : "—"}` : "",
      usageLine,
    ].filter(Boolean).join("\n");
  }

  // 表格单元格：带背景色条的数值
  function utilCell(v, cov) {
    if (v == null) return el("td", { class: "num", title: I18n.t('data_accumulating') }, ["—"]);
    const { bg } = utilColor(v);
    const txt = Math.round(v) + "%";
    const pct = Math.max(0, Math.min(100, Math.round(v)));
    const span = el("span", {
      class: "cellbar",
      style: `--util-color:${bg};--util-pct:${pct}%`,
    }, [txt]);
    const td = el("td", { class: "num", title: cov != null ? I18n.t('coverage', {pct: Math.round(cov * 100)}) : "" }, [span]);
    return td;
  }

  // ECharts 折线时序通用配置。series: [{name, points:[[ts,v]], color}]
  function lineChart(dom, series, opts) {
    opts = opts || {};
    const theme = chartTheme();
    const chart = echarts.init(dom);
    chart.setOption({
      backgroundColor: "transparent",
      tooltip: { trigger: "axis", axisPointer: { type: "line" }, backgroundColor: theme.tooltipBg, borderColor: theme.tooltipBorder, textStyle: { color: cssVar("--ink", "#f7f7f7") } },
      legend: { type: "scroll", top: 0, textStyle: { color: theme.text } },
      grid: { left: 50, right: 20, top: 36, bottom: 30 },
      xAxis: { type: "time", axisLine: { lineStyle: { color: theme.axis } }, axisLabel: { color: theme.text }, splitLine: { lineStyle: { color: theme.split } } },
      yAxis: { type: "value", min: 0, max: opts.max, name: opts.yName || "%", nameTextStyle: { color: theme.text }, axisLabel: { color: theme.text }, splitLine: { lineStyle: { color: theme.split } } },
      series: series.map((s) => ({
        name: s.name, type: "line", showSymbol: false, connectNulls: false,
        smooth: true, sampling: "lttb",
        lineStyle: s.color ? { color: s.color } : undefined,
        itemStyle: s.color ? { color: s.color } : undefined,
        data: s.points.map((p) => [p[0] * 1000, p[1]]),
      })),
    });
    return chart;
  }

  function barChart(dom, labels, values, opts) {
    opts = opts || {};
    const theme = chartTheme();
    const chart = echarts.init(dom);
    chart.setOption({
      backgroundColor: "transparent",
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, backgroundColor: theme.tooltipBg, borderColor: theme.tooltipBorder, textStyle: { color: cssVar("--ink", "#f7f7f7") } },
      grid: { left: 150, right: 24, top: 10, bottom: 30 },
      xAxis: { type: "value", name: opts.xName || "", nameTextStyle: { color: theme.text }, axisLabel: { color: theme.text }, splitLine: { lineStyle: { color: theme.split } } },
      yAxis: { type: "category", data: labels, inverse: true, axisLabel: { color: theme.text }, axisLine: { lineStyle: { color: theme.axis } } },
      series: [{ type: "bar", data: values, itemStyle: { color: opts.color || theme.bar }, barMaxWidth: 22 }],
    });
    return chart;
  }

  function ago(ts) {
    if (!ts) return I18n.t('never');
    const s = Math.max(0, Math.floor(Date.now() / 1000) - ts);
    if (s < 60) return I18n.t('ago_seconds', {n: s});
    if (s < 3600) return I18n.t('ago_minutes', {n: Math.floor(s / 60)});
    if (s < 86400) return I18n.t('ago_hours', {n: Math.floor(s / 3600)});
    return I18n.t('ago_days', {n: Math.floor(s / 86400)});
  }

  // 自定义标签：由 inventory 的 badges[] 驱动，算力域与集群共用同一套渲染
  // （库引用在后端展开成完整定义，前端只管画）。
  // 与算力域家族色解耦——标签表达的是"谁装的/什么属性"，不是"哪个域"，所以走独立的 tone 语义色。
  // 超过 MAX_BADGES 枚折叠成 "+N"，避免标签把标题挤爆。
  const MAX_BADGES = 3;
  const TONES = ["cyan", "gold", "green", "violet", "neutral"];

  function badge(b) {
    const tone = TONES.includes(b.tone) ? b.tone : "cyan";
    const text = I18n.localize(b.text_i18n ?? b.text);
    const tooltip = I18n.localize(b.tooltip_i18n ?? b.tooltip);
    return el("span", {
      class: "cfg-badge tone-" + tone,
      title: tooltip || text,
    }, [
      b.mark ? el("span", { class: "cfg-badge-mark" }, [b.mark]) : null,
      el("span", { class: "cfg-badge-who" }, [text]),
    ].filter(Boolean));
  }

  // owner: 带 badges[] 的对象 —— 集群或算力域都行
  function badgeRow(owner) {
    const list = (owner && owner.badges) || [];
    if (!list.length) return null;
    const shown = list.slice(0, MAX_BADGES);
    const rest = list.slice(MAX_BADGES);
    const kids = shown.map(badge);
    if (rest.length) {
      kids.push(el("span", {
        class: "cfg-badge tone-neutral badge-more",
        title: rest.map((b) => {
          const text = I18n.localize(b.text_i18n ?? b.text);
          const tooltip = I18n.localize(b.tooltip_i18n ?? b.tooltip);
          return (b.mark ? b.mark + " " : "") + text +
            (tooltip ? "  —  " + tooltip : "");
        }).join("\n"),
      }, ["+" + rest.length]));
    }
    return el("span", { class: "badge-row" }, kids);
  }

  return { utilColor, fmtPct, fmtGB, clusterVar, escapeHtml, Palette, el, gpuCard, gpuPlaceholder, utilCell, lineChart, barChart, ago, badgeRow };
})();
