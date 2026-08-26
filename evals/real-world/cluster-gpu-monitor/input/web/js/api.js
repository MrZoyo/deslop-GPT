// API 封装：所有后端调用集中在这里。
window.API = (function () {
  async function getJSON(url) {
    // 用 location.origin 重建为绝对 URL，剥离可能存在的 URL 内嵌凭证
    // （否则当页面以 https://user:pass@host/ 形式打开时，fetch 会拒绝带凭证的 URL）。
    const r = await fetch(new URL(url, location.origin), { credentials: "same-origin" });
    if (!r.ok) throw new Error(url + " -> HTTP " + r.status);
    return r.json();
  }
  const q = (o) => Object.entries(o).filter(([, v]) => v != null)
    .map(([k, v]) => k + "=" + encodeURIComponent(v)).join("&");
  return {
    meta: () => getJSON("/api/meta"),
    topology: () => getJSON("/api/topology"),
    overview: (w) => getJSON("/api/overview?" + q({ window: w })),
    avg: (w, scope, metric) => getJSON("/api/metrics/avg?" + q({ window: w, scope, metric })),
    avgMulti: (scope, metric) => getJSON("/api/metrics/avg_multi?" + q({ scope, metric })),
    series: (scope, id, metric, w) => getJSON("/api/metrics/series?" + q({ scope, id, metric, window: w })),
    usersTop: (w, by, limit, cluster) => getJSON("/api/users/top?" + q({ window: w, by, limit, cluster })),
    usersRanking: (w) => getJSON("/api/users/ranking?" + q({ window: w })),
    usersCurrent: () => getJSON("/api/users/current"),
    collectorStatus: () => getJSON("/api/collector/status"),
    health: () => getJSON("/api/health"),
  };
})();
