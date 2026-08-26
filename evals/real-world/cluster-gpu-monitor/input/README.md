# Cluster GPU Monitor

简体中文 | [English](README.en.md)

<p align="center">
  <a href="https://github.com/MrZoyo/cluster-gpu-monitor/tree/v0.3.2">
    <img src="https://img.shields.io/badge/CURRENT_RELEASE-v0.3.2-009688?style=for-the-badge&amp;logo=github&amp;logoColor=white" alt="当前发布版：Cluster GPU Monitor v0.3.2">
  </a>
</p>

<p align="center">
  <a href="https://github.com/MrZoyo/cluster-gpu-monitor/actions/workflows/test.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/MrZoyo/cluster-gpu-monitor/test.yml?branch=main&amp;style=for-the-badge&amp;label=TESTS&amp;logo=githubactions&amp;logoColor=white" alt="测试状态">
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/PYTHON-3.12%2B-3776AB?style=for-the-badge&amp;logo=python&amp;logoColor=white" alt="Python 3.12 或更高版本">
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/LICENSE-MIT-2EA44F?style=for-the-badge&amp;logo=opensourceinitiative&amp;logoColor=white" alt="MIT 许可证">
  </a>
</p>

用一台中心机，通过 SSH 采集多台 NVIDIA / AMD GPU 服务器，把长期利用率、用户 GPU·小时和
空占情况存进 SQLite。目标节点无需安装 agent，也不要求 Slurm、Kubernetes 或 root 权限。

**它回答“要不要加卡”，不只回答“现在哪张卡空着”。**

[在线演示](https://mrzoyo.github.io/cluster-gpu-monitor/) ·
[文档目录](docs/README.md) ·
[配置参考](docs/CONFIGURATION.md) ·
[原生部署](docs/DEPLOYMENT.md) ·
[Docker Compose](docs/DOCKER.md)

## 为什么用它

常见的免 agent 看板擅长展示当前进程，但不保存长期历史；Prometheus / DCGM 栈能保存历史，
却需要在每台节点部署组件；HPC 计费系统通常依赖调度器。Cluster GPU Monitor 补上了中间这块：
**免 agent 采集、长期历史和按用户名归属同时成立。**

| 方案 | 免 agent | 长期历史 | 按用户归属 | 需要调度器 |
| --- | :---: | :---: | :---: | :---: |
| 多机实时看板 | 是 | 否 | 是 | 否 |
| DCGM + Prometheus | 否 | 是 | 有限 | 否 |
| HPC 作业计费 | 否 | 是 | 是 | 是 |
| **Cluster GPU Monitor** | **是** | **是** | **是** | **否** |

适合几台到几十台自管 GPU 服务器、没有统一调度器、需要用历史数据讨论扩容的团队。
上千节点遥测、秒级告警、配额或账单结算，应使用更完整的集群监控和调度系统。

## 核心能力

- **长期利用率**：12 小时到 1 个月的滚动平均，支持总览、集群、主机和单卡下钻。
- **用户 GPU·小时**：按操作系统用户名跨机器聚合，并按算力域、集群和主机拆分。
- **空占检测**：标出占用显存但近期利用率低于 5% 的 GPU。
- **多集群拓扑**：算力域 → 集群 → 主机三层结构，支持多语言标签与备注、待接入和软退役。
- **NVIDIA 与 AMD**：支持自动探测 `nvidia-smi`、`amd-smi` 或 `rocm-smi`；已知厂商时可在
  inventory 填写 `vendor`，跳过每轮额外探测。
- **轻量自托管**：SQLite、FastAPI、原生 JavaScript 和本地 ECharts，无前端构建步骤。

## 快速开始

中心机需要 Python 3.12+、[uv](https://docs.astral.sh/uv/) 和系统 `ssh`；目标节点需要
`bash`、`ps`、coreutils 及厂商 SMI 工具。

```bash
git clone https://github.com/MrZoyo/cluster-gpu-monitor.git
cd cluster-gpu-monitor
uv sync

cp config/inventory.example.yaml config/inventory.yaml
cp config/settings.example.toml config/settings.toml
$EDITOR config/inventory.yaml

SSH_ALIAS=my-a-1                  # 改成 inventory 中的一条 ssh_alias
ssh "$SSH_ALIAS" true             # 确认可以免交互登录
uv run gpumon config-check        # 校验拓扑、期望卡数和运行参数
uv run gpumon initdb
uv run gpumon collect --once      # 先试采一轮
uv run gpumon web                 # http://127.0.0.1:8848/
```

`inventory.yaml` 中的 `ssh_alias` 必须对应中心机 `~/.ssh/config` 里的条目。跳板机、端口、
密钥和主机密钥策略都留在 SSH 配置中；采集器直接调用系统 `ssh`，不会覆盖这些设置。

从另一台电脑查看时，可先建立隧道：

```bash
ssh -N -L 8848:127.0.0.1:8848 <monitor-host>
```

然后打开 `http://127.0.0.1:8848/`。原生常驻运行、systemd、备份和 HTTPS 配置见
[部署指南](docs/DEPLOYMENT.md)；容器运行见 [Docker Compose 指南](docs/DOCKER.md)。

## 两种部署方式

| 方式 | 适合场景 | 指南 |
| --- | --- | --- |
| Python + systemd | 小规格宿主、需要完整 systemd 加固与原子 release 回滚 | [原生部署](docs/DEPLOYMENT.md) |
| Docker Compose | 快速安装、环境隔离、已有容器运维体系 | [Docker Compose 部署](docs/DOCKER.md) |

两种方式使用同一份 inventory、settings 和 SQLite 数据模型。容器版仍通过 SSH 采集远端 GPU，
不需要 NVIDIA Container Toolkit。切换部署方式前必须停止旧 collector，禁止两个 collector
同时写同一数据库。

## 工作方式

```text
GPU 节点（不安装 agent）
    ↑  ssh <alias> bash -s
采集器：GPU / 进程 / CPU / 内存 / load
    ↓
SQLite：原始样本 → 5 分钟聚合 → 1 小时聚合
    ↓
FastAPI /api/* → 原生 HTML + JavaScript + 本地 ECharts
```

- 远端脚本从 stdin 执行，不在节点落文件。
- 原始样本支持用户归属；两级聚合让长时间窗查询保持轻量。
- GPU 卡片同时区分近期状态与所选时间窗均值，避免训练步间的瞬时抖动误导判断。
- Web 与采集器可以使用不同系统账户；Web 只读 SQLite，也不需要读取 SSH 密钥。

查询窗口、数据生命周期、指标语义和安全边界见[架构与设计取舍](docs/ARCHITECTURE.md)。

## 最小配置

```yaml
version: 1

clusters:
  - key: training
    name: "训练集群"
    hosts:
      - key: node-1
        ssh_alias: gpu-node-1
        display_name: "GPU Node 1"
        gpu_count: 8
```

`key` 是历史数据的稳定标识，上线后不要修改；地址、端口和跳板变化时只调整 `ssh_alias`
及 `~/.ssh/config`。完整字段、标签、AMD、保留期、并发和查询边界见
[配置参考](docs/CONFIGURATION.md)。

## 生产部署与安全

`gpumon web` **没有内置认证**，默认只监听 `127.0.0.1`。对团队开放时必须放在带认证的
HTTPS 反向代理之后；仓库同时提供原生 systemd/Caddy 部署和 Docker Compose 部署。

生产部署建议：

- 隔离 collector / backup 与 Web 的权限；Web 不持有 SSH key，也不能写数据库。
- 把真实 `inventory.yaml`、`settings.toml`、口令 hash、DNS token 和私钥留在部署机。
- 使用不可变 release 或镜像、独立配置和数据目录，并保留可回滚的上一版本。
- 使用内置 SQLite 在线备份，不要直接复制正在写入的 WAL 数据库。

完整安装、HTTPS、日常运维、排障与回滚步骤见[原生部署指南](docs/DEPLOYMENT.md)或
[Docker Compose 指南](docs/DOCKER.md)。

## 文档

| 目标 | 简体中文 | English |
| --- | --- | --- |
| 选择文档 | [文档目录](docs/README.md) | [Documentation index](docs/README.en.md) |
| 配置机器与运行参数 | [配置参考](docs/CONFIGURATION.md) | [Configuration reference](docs/CONFIGURATION.en.md) |
| 理解采集、存储与指标 | [架构与设计取舍](docs/ARCHITECTURE.md) | [Architecture and trade-offs](docs/ARCHITECTURE.en.md) |
| 生成或发布演示数据 | [Demo 指南](docs/DEMO.md) | [Demo guide](docs/DEMO.en.md) |
| 原生部署、运维与排障 | [部署指南](docs/DEPLOYMENT.md) | [Deployment guide](docs/DEPLOYMENT.en.md) |
| Docker Compose 部署 | [Docker 指南](docs/DOCKER.md) | [Docker guide](docs/DOCKER.en.md) |

## 已知边界

- 用户归属来自远端 `ps` 的操作系统用户名，不等同于调度器作业、项目或成本中心。
- NVIDIA 路径长期运行；AMD 解析器有构造样本测试，但尚未在真实 AMD 硬件上闭环验证。
- SQLite 适合小到中等规模的自管集群，不面向上千节点高频遥测。
- 项目没有内置登录、权限系统和告警引擎；访问控制由网络和反向代理负责。

## 开发

```bash
uv sync --extra dev
uv run pytest -q
python3 scripts/check_added_secrets.py --self-test
python3 scripts/check_added_secrets.py --staged
```

后端在 `src/gpumon/`，前端在 `web/`。提交问题或补丁前，请说明 GPU 厂商、SMI 版本、
复现命令和脱敏后的输出；不要提交真实拓扑、用户名、凭据或数据库。

## 许可

[MIT](LICENSE)
