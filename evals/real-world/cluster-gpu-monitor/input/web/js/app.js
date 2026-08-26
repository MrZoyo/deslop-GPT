// 应用入口：全局状态、hash 路由、顶栏时间窗切换、健康灯、自动刷新、图表尺寸管理。
window.GM = (function () {
  const state = { meta: { windows: ["12h", "24h", "48h", "72h", "1w", "2w", "1m"] }, window: "24h", theme: "dark" };
  let charts = [];        // 当前视图的 ECharts 实例，切换视图前统一 dispose
  let refreshTimer = null;

  function go(path) { location.hash = "#" + path; }
  function crumb(text) { document.getElementById("crumb").textContent = text; }

  function buildLangSwitch() {
    const box = document.getElementById("langSwitch");
    if (!box) return;
    box.innerHTML = "";
    const btn = UI.el("button", {
      class: "lang-btn",
      title: I18n.getLocale() === 'zh' ? '切换语言 / Switch Language' : 'Switch Language / 切换语言',
      onclick: () => {
        const dropdown = box.querySelector(".lang-dropdown");
        if (dropdown) {
          dropdown.remove();
        } else {
          showLangDropdown(box);
        }
      },
    }, []);
    const icon = document.createElement("img");
    icon.src = "icons/globe.svg";
    icon.className = "topbar-icon";
    btn.appendChild(icon);
    box.appendChild(btn);
  }

  function showLangDropdown(container) {
    const dropdown = UI.el("div", { class: "lang-dropdown" }, [
      UI.el("div", {
        class: "lang-option" + (I18n.getLocale() === 'zh' ? ' active' : ''),
        onclick: () => { I18n.setLocale('zh'); dropdown.remove(); },
      }, ["中文"]),
      UI.el("div", {
        class: "lang-option" + (I18n.getLocale() === 'en' ? ' active' : ''),
        onclick: () => { I18n.setLocale('en'); dropdown.remove(); },
      }, ["English"]),
    ]);
    container.appendChild(dropdown);
    // 点击外部关闭
    setTimeout(() => {
      const close = (e) => {
        if (!container.contains(e.target)) {
          dropdown.remove();
          document.removeEventListener("click", close);
        }
      };
      document.addEventListener("click", close);
    }, 0);
  }
  function onResize(chart) { charts.push(chart); }
  function disposeCharts() { charts.forEach((c) => { try { c.dispose(); } catch (e) {} }); charts = []; }

  function updateDemoBanner() {
    const title = document.getElementById("demo-banner-title");
    const text = document.getElementById("demo-banner-text");
    const link = document.getElementById("demo-banner-link");
    if (title) title.textContent = I18n.t('demo_banner_title');
    if (text) text.textContent = I18n.t('demo_banner_text');
    if (link) link.textContent = I18n.t('demo_banner_link');
  }

  function applyTheme() {
    document.body.dataset.theme = state.theme === "light" ? "light" : "dark";
  }

  function setTheme(theme) {
    state.theme = theme === "light" ? "light" : "dark";
    localStorage.setItem("gpumon.theme", state.theme);
    applyTheme();
    buildThemeSwitch();
    render();
  }

  function parseRoute() {
    const h = location.hash.replace(/^#/, "") || "/";
    const seg = h.split("/").filter(Boolean);     // ["cluster","h200"]
    if (seg.length === 0) return { view: "overview", params: {} };
    if (seg[0] === "cluster") return { view: "cluster", params: { key: decodeURIComponent(seg[1]) } };
    if (seg[0] === "host") return { view: "host", params: { key: decodeURIComponent(seg[1]) } };
    if (seg[0] === "gpu") return { view: "gpu", params: { id: seg[1] } };
    if (seg[0] === "ranking") return { view: "ranking", params: {} };
    return { view: "overview", params: {} };
  }

  async function render() {
    const route = parseRoute();
    const root = document.getElementById("view");
    const nav = document.getElementById("navRank");
    if (nav) nav.classList.toggle("active", route.view === "ranking");
    disposeCharts();
    try {
      await Views[route.view].render(root, route.params);
    } catch (e) {
      root.innerHTML = "";
      root.appendChild(UI.el("div", { class: "panel" }, [
        UI.el("h3", {}, [I18n.t('load_failed')]),
        UI.el("div", { class: "note" }, [e && e.message ? e.message : String(e)]),
      ]));
      console.error(e);
    }
    scheduleRefresh(route.view);
  }

  // 仅总览页自动刷新，避免打断下钻页的交互（如指标切换）
  function scheduleRefresh(view) {
    if (refreshTimer) clearInterval(refreshTimer);
    if (view === "overview") {
      refreshTimer = setInterval(() => { if (parseRoute().view === "overview") render(); },
        (state.meta.poll_interval_s || 30) * 1000);
    }
  }

  function buildWinSwitch() {
    const box = document.getElementById("winSwitch");
    box.innerHTML = "";
    state.meta.windows.forEach((w) => {
      const b = UI.el("button", {
        class: w === state.window ? "active" : "",
        onclick: () => {
          state.window = w;
          localStorage.setItem("gpumon.window", w);
          buildWinSwitch();
          render();
        },
      }, [w]);
      box.appendChild(b);
    });
  }

  function buildThemeSwitch() {
    const box = document.getElementById("themeSwitch");
    if (!box) return;
    box.innerHTML = "";
    [["dark", "moon.svg"], ["light", "sun.svg"]].forEach(([key, icon]) => {
      const b = UI.el("button", {
        class: key === state.theme ? "active" : "",
        title: I18n.t('theme_' + key),
        onclick: () => setTheme(key),
      }, []);
      const img = document.createElement("img");
      img.src = "icons/" + icon;
      img.className = "topbar-icon";
      b.appendChild(img);
      box.appendChild(b);
    });
  }

  async function pollHealth() {
    const dot = document.getElementById("hdot");
    const txt = document.getElementById("htext");
    try {
      const [st, hl] = await Promise.all([API.collectorStatus(), API.health()]);
      const activeHosts = st.hosts.filter((h) => h.status !== "planned");
      const online = activeHosts.filter((h) => h.online).length;
      const total = activeHosts.length;
      const age = hl.last_sample_age_s;
      let cls = "green";
      if (online === 0 || age == null) cls = "red";
      else if (online < total || (age != null && age > 90)) cls = "yellow";
      dot.className = "dot " + cls;
      txt.textContent = I18n.t('health_online', {online, total, time: UI.ago(hl.last_sample_ts)});
      dot.parentElement.title = activeHosts.map((h) =>
        `${h.display_name}: ${h.online ? I18n.t('health_host_online') : I18n.t('health_host_offline')} ${I18n.t('health_cards', {seen: h.gpus_seen ?? 0, expected: h.gpus_expected})}` +
        (h.last_error ? " (" + h.last_error + ")" : "")).join("\n");
    } catch (e) {
      dot.className = "dot red"; txt.textContent = I18n.t('service_unreachable');
    }
  }

  async function init() {
    I18n.init();
    state.theme = localStorage.getItem("gpumon.theme") === "light" ? "light" : "dark";
    applyTheme();
    try { state.meta = await API.meta(); } catch (e) {}
    // 把"算力域 → 色带"映射交给 Palette，之后所有身份色都按 inventory 配置走
    UI.Palette.setGroups(state.meta.capacity_groups);
    // 恢复保存的时间窗，默认 24h
    const savedWindow = localStorage.getItem("gpumon.window");
    if (savedWindow && state.meta.windows.includes(savedWindow)) {
      state.window = savedWindow;
    } else if (!state.meta.windows.includes(state.window)) {
      state.window = state.meta.windows[1] || state.meta.windows[0];
    }
    buildLangSwitch();
    buildThemeSwitch();
    buildWinSwitch();
    updateDemoBanner();
    // 设置 navRank 文字
    document.getElementById("navRankText").textContent = I18n.t('user_ranking');
    window.addEventListener("hashchange", render);
    window.addEventListener("resize", () => charts.forEach((c) => { try { c.resize(); } catch (e) {} }));
    document.getElementById("title").onclick = () => go("/");
    document.getElementById("navRank").onclick = () => go("/ranking");
    document.querySelector(".health").onclick = () => go("/");
    await render();
    pollHealth();
    setInterval(pollHealth, 15000);
  }

  return { state, go, crumb, onResize, buildLangSwitch, buildThemeSwitch, buildWinSwitch, updateDemoBanner, init };
})();

document.addEventListener("DOMContentLoaded", GM.init);
