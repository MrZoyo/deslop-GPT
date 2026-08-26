#!/usr/bin/env python3
"""把演示库导出成**纯静态站点** —— 可直接丢 GitHub Pages，不需要任何后端。

原理：前端所有请求都经 web/js/api.js 的一个 getJSON()，且这些接口都是只读的。
于是把每个接口在"某一时刻"的响应快照成 JSON 文件，再注入一小段 shim 把
`/api/xxx?window=24h` 改写成 `api/xxx.24h.json`，前端代码一行不用改。

代价与取舍：
  - 时间是**冻结**的。页面上的"更新于 x 秒前"会随真实时钟越走越远，
    所以 shim 会把 meta.server_time 之外的时间基准也一起冻住（见 _freeze_js）。
  - 时序被**抽稀**到最多 MAX_POINTS 点。图表本来就用 lttb 采样显示，
    视觉上无差别，但能把体积压下来一个量级。
  - 只导出前端真的会请求的参数组合（见 api.js 各 View 的调用点），
    不做全参数笛卡尔积。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(_ROOT / "src"))
sys.path.append(str(Path(__file__).resolve().parent))

from demo_safety import (  # noqa: E402
    DemoSafetyError,
    assert_safe_export_directory,
    assert_safe_export_input,
    demo_database_state,
    is_demo_inventory,
    mark_static_output,
    safe_child,
    static_output_is_marked,
)

MAX_POINTS = 300      # 每条时序最多保留的点数（抽稀上限）
METRICS = ["util_gpu", "util_mem", "mem_used", "temp", "power"]


def decimate(points: list, cap: int = MAX_POINTS) -> list:
    """等间隔抽稀到 cap 点以内。保留首尾，避免曲线两端被截断。"""
    n = len(points)
    if n <= cap:
        return points
    step = n / cap
    out = [points[int(i * step)] for i in range(cap)]
    if out[-1] is not points[-1]:
        out[-1] = points[-1]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="export_static_demo.py",
        description="把演示库导出为可直接托管的静态站点（GitHub Pages 等）")
    ap.add_argument("--db", required=True, help="演示数据库（gen_demo_db.py 产出）")
    ap.add_argument("--inventory", required=True, help="配套 inventory YAML")
    ap.add_argument(
        "--settings",
        default=str(_ROOT / "config" / "settings.example.toml"),
        help="配套 settings TOML（默认使用公开示例配置）",
    )
    ap.add_argument("--out", default="dist/demo", help="输出目录")
    ap.add_argument("--force", action="store_true", help="清空已存在的输出目录")
    ap.add_argument(
        "--allow-unmarked-inputs",
        action="store_true",
        help="显式允许非 generator 产出的输入（可能公开真实拓扑/用户名，慎用）",
    )
    args = ap.parse_args(argv)

    try:
        db = assert_safe_export_input(Path(args.db), kind="database")
        inv = assert_safe_export_input(Path(args.inventory), kind="inventory")
        settings = assert_safe_export_input(Path(args.settings), kind="settings")
        out = assert_safe_export_directory(Path(args.out))
        if not args.allow_unmarked_inputs:
            if demo_database_state(db) != "complete":
                raise DemoSafetyError("数据库缺少完整的 synthetic demo 生成标记")
            if not is_demo_inventory(inv):
                raise DemoSafetyError("inventory 缺少 synthetic demo 生成标记")
    except DemoSafetyError as exc:
        print(f"拒绝导出：{exc}", file=sys.stderr)
        return 2

    # 删除输出前先完整解析输入；配置错误不应让一个本来可用的静态站点先被清空。
    try:
        import yaml
        from gpumon.models import Inventory, Settings

        inventory_model = Inventory.model_validate(yaml.safe_load(inv.read_text(encoding="utf-8")))
        with settings.open("rb") as handle:
            settings_model = Settings.model_validate(tomllib.load(handle))
    except Exception as exc:
        print(f"输入配置无效，拒绝导出: {type(exc).__name__}", file=sys.stderr)
        return 2

    if args.allow_unmarked_inputs:
        print("警告：已显式允许未标记输入，请确认其中没有真实拓扑或用户名。", file=sys.stderr)

    if out.exists():
        if not args.force:
            print(f"{out} 已存在，加 --force 覆盖。", file=sys.stderr)
            return 2
        if not static_output_is_marked(out):
            print(f"拒绝递归删除没有静态 demo 标记的目录: {out}", file=sys.stderr)
            return 2
        shutil.rmtree(out)
    api = out / "api"
    api.mkdir(parents=True)
    mark_static_output(out)

    # 关键：让 gpumon 的配置层指向演示库与演示清单。
    # config 模块用 lru_cache 缓存，所以必须在 import 之前把环境准备好——
    # 这里的做法是直接改模块级变量并清缓存，比起改环境变量更好控制。
    import gpumon.config as cfg

    cfg.load_inventory.cache_clear()
    cfg.load_settings.cache_clear()
    def _inv():
        return inventory_model

    def _settings():
        return settings_model

    cfg.load_inventory = _inv                      # type: ignore[assignment]
    cfg.load_settings = _settings                  # type: ignore[assignment]
    cfg.db_path = lambda: db                       # type: ignore[assignment]

    # routes/deps 在 import 时就绑定了 config 的名字，故要在改完之后再 import
    import gpumon.api.deps as deps
    import gpumon.db.store as store_module
    from gpumon.db.store import WINDOWS, Store

    # 同一解释器里可能先运行过其它 gpumon 代码（测试/嵌入式调用）；此时 store 模块
    # 已经绑定了旧配置函数，不能只依赖“首次 import”的顺序假设。
    store_module.load_inventory = _inv            # type: ignore[assignment]
    store_module.load_settings = _settings        # type: ignore[assignment]
    deps.get_store.cache_clear()
    store = Store(db)
    deps.get_store = lambda: store                 # type: ignore[assignment]

    # 把"现在"钉在最后一条样本的时刻，再让各接口照常计算。
    #
    # 为什么必须这么做：online、last_sample_age_s、近 10 分钟均值全都是
    # 「now - ts」算出来的。导出发生在造数之后（哪怕只差几分钟），
    # 用真实时钟就会把所有机器算成离线、把实时值算成过期 —— 导出的快照一开就是
    # 满屏"离线"。钉住 now 之后，快照内部自洽：前端那边也把 Date.now 冻在
    # meta.server_time（= 同一时刻），于是"更新于 x 秒前"显示为刚刚。
    with store.connect() as _c:
        latest = _c.execute("SELECT MAX(ts) FROM sample_gpu").fetchone()[0]
    if latest:
        import time as _time
        _time.time = lambda _t=float(latest): _t   # type: ignore[assignment]
        print(f"（已把导出时刻钉在最后一条样本 ts={latest}）")

    import gpumon.api.routes as routes
    routes.load_inventory = _inv                   # type: ignore[assignment]
    routes.load_settings = _settings               # type: ignore[assignment]
    routes.get_store = lambda: store               # type: ignore[assignment]

    written: list[tuple[str, int]] = []

    def dump(name: str, obj) -> None:
        p = safe_child(api, name)
        p.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")),
                     encoding="utf-8")
        written.append((name, p.stat().st_size))

    print("导出接口快照…")
    dump("live.json", routes.live())
    meta = routes.meta()
    dump("meta.json", meta)
    dump("topology.json", routes.topology())
    dump("health.json", routes.health())
    dump("collector_status.json", routes.collector_status())
    dump("users_current.json", routes.users_current())

    windows = list(WINDOWS)
    for w in windows:
        dump(f"overview.{w}.json", routes.overview(window=w))
        dump(f"users_ranking.{w}.json", routes.users_ranking(window=w))

    # avg_multi：前端只用 host / gpu 两个 scope 的 util_gpu
    for scope in ("host", "gpu"):
        dump(f"avg_multi.{scope}.util_gpu.json",
             routes.metrics_avg_multi(scope=scope, metric="util_gpu"))

    # users_top：集群页用（每集群 x 每窗口）
    topo = routes.topology()
    cluster_keys = [c["key"] for c in topo["clusters"]]
    for w in windows:
        for ck in cluster_keys:
            dump(f"users_top.{w}.{ck}.json",
                 routes.users_top(window=w, by="gpu_hours", limit=10, cluster=ck))

    # 时序：打成"每 (scope,metric,window) 一个包"，包内按 id 索引。
    # 不按 (gpu,metric,window) 拆文件——那是几千个小文件，Pages 上首屏会被请求数拖死。
    print("导出时序（抽稀到 %d 点以内）…" % MAX_POINTS)
    gpu_ids, host_ids, cluster_ids = [], [], []
    for c in topo["clusters"]:
        if c.get("id") is not None:
            cluster_ids.append(c["id"])
        for h in c["hosts"]:
            if h.get("id") is not None:
                host_ids.append(h["id"])
            for g in h.get("gpus", []):
                # /api/topology 的卡行来自 gpu_card 表，主键列叫 id；
                # /api/overview 里同一张卡叫 gpu_id。两边都兼容，别假设只有一种。
                gid = g.get("gpu_id", g.get("id"))
                if gid is not None:
                    gpu_ids.append(gid)

    for w in windows:
        for metric in METRICS:
            bundle = {str(i): decimate(store.get_series("gpu", i, metric, w))
                      for i in gpu_ids}
            dump(f"series.gpu.{metric}.{w}.json", bundle)
        for scope, ids in (("cluster", cluster_ids), ("host", host_ids)):
            bundle = {str(i): decimate(store.get_series(scope, i, "util_gpu", w))
                      for i in ids}
            dump(f"series.{scope}.util_gpu.{w}.json", bundle)

    # 前端：整份 web/ 拷过去，再注入静态 shim
    print("拷贝前端并注入静态 shim…")
    for item in ("css", "js", "vendor", "icons", "index.html"):
        src = _ROOT / "web" / item
        dst = safe_child(out, item)
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    safe_child(out, "js/static-demo.js").write_text(_SHIM_JS, encoding="utf-8")
    index_path = safe_child(out, "index.html")
    idx = index_path.read_text(encoding="utf-8")
    # shim 必须在 api.js 之前加载：它要在 API 定义前就把 fetch 换掉
    idx = idx.replace('<script src="/js/api.js"></script>',
                      '<script src="js/static-demo.js"></script>\n'
                      '  <script src="js/api.js"></script>')
    # 绝对路径改相对，才能放在 <user>.github.io/<repo>/ 这种子路径下
    idx = idx.replace('href="/css/', 'href="css/').replace('src="/js/', 'src="js/') \
             .replace('src="/vendor/', 'src="vendor/').replace('src="/icons/', 'src="icons/')
    idx = idx.replace("<title>GPU 集群占用监控</title>",
                      "<title>GPU 集群占用监控 · 在线演示（数据为虚构示例）</title>")
    idx = idx.replace('<div class="wrap">', _BANNER_HTML + '\n  <div class="wrap">')
    index_path.write_text(idx, encoding="utf-8")

    # Pages 不要跑 Jekyll，否则下划线开头的目录会被吞掉
    safe_child(out, ".nojekyll").write_text("", encoding="utf-8")

    total = sum(s for _, s in written)
    print(f"\n完成：{len(written)} 个 JSON，共 {total/1024/1024:.1f} MB")
    biggest = sorted(written, key=lambda x: -x[1])[:5]
    print("最大的几个：")
    for name, size in biggest:
        print(f"  {name:44s} {size/1024:8.0f} KB")
    site = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"整站体积：{site/1024/1024:.1f} MB")
    print(f"\n本地预览：cd {out} && python3 -m http.server 8080")
    return 0


_BANNER_HTML = """  <div class="demo-banner">
    <b id="demo-banner-title">演示站点</b>
    <span id="demo-banner-text">数据为虚构示例（算力域 / 集群 / 用户名均为编造），时间冻结于导出时刻。</span>
    <a id="demo-banner-link" href="https://github.com/MrZoyo/cluster-gpu-monitor">源码与部署说明 →</a>
  </div>"""


# 这段 shim 的职责：把 fetch("/api/...") 改写成读同目录下的静态 JSON。
# 放在 api.js 之前加载，这样 api.js 里的 getJSON 拿到的是被换过的 fetch。
_SHIM_JS = r"""// 静态演示模式：拦截 /api/* 请求，改读导出的 JSON 快照。
// 由 scripts/export_static_demo.py 注入，正常部署里没有这个文件。
(function () {
  const origFetch = window.fetch.bind(window);

  // 把 /api/xxx?a=1&b=2 映射到导出时用的文件名。
  // 命名规则与 export_static_demo.py 里的 dump() 一一对应，改一边要改两边。
  function mapPath(url) {
    const u = new URL(url, location.href);
    if (!u.pathname.includes("/api/")) return null;
    const ep = u.pathname.split("/api/")[1].replace(/\/$/, "");
    const p = u.searchParams;
    const w = p.get("window");
    switch (ep) {
      case "live": return "live.json";
      case "meta": return "meta.json";
      case "topology": return "topology.json";
      case "health": return "health.json";
      case "collector/status": return "collector_status.json";
      case "users/current": return "users_current.json";
      case "overview": return `overview.${w}.json`;
      case "users/ranking": return `users_ranking.${w}.json`;
      case "metrics/avg_multi":
        return `avg_multi.${p.get("scope")}.${p.get("metric")}.json`;
      case "users/top":
        return `users_top.${w}.${p.get("cluster")}.json`;
      case "metrics/series":
        // 时序是按 (scope,metric,window) 打的包，包内按 id 取——见下面的 unwrap
        return `series.${p.get("scope")}.${p.get("metric")}.${w}.json|${p.get("id")}`;
      default: return null;
    }
  }

  // 相对于 index.html 所在目录，这样放子路径（<user>.github.io/<repo>/）也能用
  const base = location.pathname.replace(/[^/]*$/, "");

  window.fetch = async function (input, init) {
    // api.js 传进来的是 **URL 对象**（它用 new URL(url, location.origin) 重建过），
    // 不是字符串。只判 typeof==="string" 会漏掉，请求就直接打到真后端上 404。
    // Request 对象走 .url，URL 对象走 toString()。
    let url = null;
    if (typeof input === "string") url = input;
    else if (input instanceof URL) url = input.href;
    else if (input && typeof input.url === "string") url = input.url;
    const mapped = url ? mapPath(url) : null;
    if (!mapped) return origFetch(input, init);

    const [file, id] = mapped.split("|");
    const r = await origFetch(base + "api/" + file, init);
    if (!r.ok) return r;
    const data = await r.json();
    // series 请求：从包里取出该 id 的点集，还原成后端的 {points: [...]} 形状
    const body = (id !== undefined)
      ? { scope: null, id: Number(id), metric: null, window: null, points: data[id] || [] }
      : data;
    return new Response(JSON.stringify(body),
      { status: 200, headers: { "Content-Type": "application/json" } });
  };

  // 时间冻结：导出后真实时钟还在走，若不处理，"更新于 x 分钟前"会一直变大，
  // 几天后变成"3 天前"，看起来像站挂了。
  //
  // ⚠️ 只能改 Date.now，**绝不能替换 Date 构造函数**。
  // zrender（ECharts 的渲染层）的动画时钟是 `function(){return (new Date).getTime()}`。
  // 一旦把无参 new Date() 也钉住，每帧算出的 elapsed 恒为 0，补间动画永远停在第 0 帧
  // —— 条形图的条宽从 0 开始长，于是"条一根都看不见"，只剩坐标轴和标签。
  // （headless 截图看不出来：--virtual-time-budget 会把动画快进完，真实浏览器才复现。）
  //
  // 前端只有 components.js 的 ago() 用 Date.now()，改这一个静态方法就够。
  origFetch(base + "api/meta.json").then((r) => r.json()).then((m) => {
    if (!m || !m.server_time) return;
    Date.now = () => m.server_time * 1000;
  }).catch(() => {});
})();
"""


if __name__ == "__main__":
    sys.exit(main())
