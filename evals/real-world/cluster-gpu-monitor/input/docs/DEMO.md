# Demo 指南

简体中文 | [English](DEMO.en.md) | [文档目录](README.md) | [在线演示](https://mrzoyo.github.io/cluster-gpu-monitor/)

Demo 工具生成虚构拓扑、用户名和 GPU 历史，不需要任何 GPU 节点。它既可用于本地体验，也可
把真实前端导出为纯静态站点。

> 不要把真实 inventory、settings 或生产数据库用于公开静态导出。导出的 JSON 会包含输入
> 数据中的显示名称、主机元数据、用户名和进程名。

## 本地运行虚构数据

下面使用临时状态目录，不会覆盖仓库中的真实配置：

```bash
uv sync

DEMO_ROOT="$(mktemp -d)"
uv run python scripts/gen_demo_db.py \
  --scale small --days 3 \
  --db "$DEMO_ROOT/data/demo.db" \
  --inventory "$DEMO_ROOT/config/inventory.demo.yaml"

cp "$DEMO_ROOT/config/inventory.demo.yaml" "$DEMO_ROOT/config/inventory.yaml"
sed 's#path = "data/gpumon.db"#path = "data/demo.db"#' \
  config/settings.example.toml > "$DEMO_ROOT/config/settings.demo.toml"
cp "$DEMO_ROOT/config/settings.demo.toml" "$DEMO_ROOT/config/settings.toml"

GPUMON_ROOT="$DEMO_ROOT" uv run gpumon config-check
GPUMON_ROOT="$DEMO_ROOT" uv run gpumon web
```

打开 `http://127.0.0.1:8848/`。退出 Web 后可删除终端打印的临时目录；它不是项目运行所需
文件。

### 规模与时间范围

| 参数 | 拓扑 | 适用场景 |
| --- | --- | --- |
| `--scale small` | 2 个算力域、3 个集群、6 台主机、48 张 GPU | 快速体验与日常开发 |
| `--scale large` | 4 个算力域、9 个集群、32 台主机、256 张 GPU | 大页面与查询性能检查 |

3 天数据可以让 12h、24h、48h 和 72h 窗口都有可用曲线；更长窗口会正常显示“数据积累中”。
生成 31 天数据会产生数百万行乃至 GB 级数据库，只在确实需要验证月窗口时使用。

虚构数据覆盖满载、空占、离线、少卡、待接入、退役、AMD 和标签折叠等界面状态。
`--seed` 控制可复现随机数，默认值已经固定。

## 导出静态站点

在上一步生成数据后运行：

```bash
uv run python scripts/export_static_demo.py \
  --db "$DEMO_ROOT/data/demo.db" \
  --inventory "$DEMO_ROOT/config/inventory.demo.yaml" \
  --settings "$DEMO_ROOT/config/settings.demo.toml" \
  --out dist/demo

cd dist/demo
python3 -m http.server 8080
```

打开 `http://127.0.0.1:8080/`。输出目录已存在时，只有确认它由本工具标记后才能加
`--force` 覆盖。

导出器会：

1. 在最后一条样本的时间点调用真实 API 代码并保存 JSON 响应。
2. 复制未经改写的前端资源，注入一个把 `/api/*` 映射到 JSON 的小型 shim。
3. 把每条时序抽稀到最多 300 点，并按 scope / metric / window 打包。
4. 冻结页面相对时间，避免静态站几天后看起来像采集器已经离线。

静态站没有后端、SSH 或数据库写入能力；它只是某个时刻的只读快照。

## 发布到 GitHub Pages

仓库的 [demo workflow](../.github/workflows/demo.yml) 会生成 large / 3 天数据、导出站点并
上传到 GitHub Pages。生成数据库和导出产物都不提交进 Git。

修改前端、API、Demo fixtures 或生成/导出脚本后，push 到 `main` 会触发工作流；也可以在
Actions 页面手工执行 `workflow_dispatch`。

## 防误操作机制

生成器和导出器默认 fail closed：

- 生成器拒绝覆盖真实运行文件、示例配置、危险路径和名为 `gpumon.db` 的数据库。
- `--force` 只能覆盖带正确 synthetic 标记的 Demo 数据。
- 导出器默认只接受状态为 complete 的生成库与配套标记清单。
- 导出目录不能是 home、仓库根、运行根或源码目录；递归覆盖只允许已标记的旧输出。
- `--allow-unmarked-inputs` 会绕过“必须由生成器创建”的限制，但不会解除危险路径保护。

`--allow-unmarked-inputs` 只用于人工构造且确认无真实信息的数据。不要为了省一步而对生产库
使用它。
