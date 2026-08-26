# 文档目录

简体中文 | [English](README.en.md) | [返回项目首页](../README.md)

README 负责说明项目是否适合你，并提供最短可运行路径。这里按任务列出更完整的文档，
不用从一篇很长的手册里寻找入口。

## 从哪里开始

| 你想做什么 | 从这里开始 | 里面有什么 |
| --- | --- | --- |
| 第一次运行项目 | [README 快速开始](../README.md#快速开始) | 安装依赖、准备配置、试采一轮、打开网页 |
| 添加机器或调整运行参数 | [配置参考](CONFIGURATION.md) | inventory、settings、状态、标签、保留期与并发 |
| 理解数据口径 | [架构与设计取舍](ARCHITECTURE.md) | SSH 采集、SQLite、聚合、在线状态、GPU·小时与安全边界 |
| 生成虚构数据或静态站点 | [Demo 指南](DEMO.md) | 本地演示、GitHub Pages 导出及防误操作机制 |
| 使用 Python + systemd 部署 | [原生部署指南](DEPLOYMENT.md) | release 布局、systemd、Caddy、备份、迁移与排障 |
| 使用容器部署 | [Docker Compose 指南](DOCKER.md) | 非 root 镜像、权限隔离、SSH 挂载、备份与升级 |

## 推荐阅读路径

### 先在本机试用

1. 按 [README 快速开始](../README.md#快速开始)准备两个配置文件。
2. 用 `ssh <alias> true` 确认中心机能免交互登录目标节点。
3. 运行 `gpumon config-check` 和 `gpumon collect --once`。
4. 遇到字段问题时查[配置参考](CONFIGURATION.md)，不要从部署手册开始。

没有 GPU 节点也可以试用：按 [Demo 指南](DEMO.md)生成完全虚构的数据。

### 准备生产部署

1. 先读[架构与设计取舍](ARCHITECTURE.md)中的安全边界，确认 Web 无内置认证。
2. 在 [Python + systemd](DEPLOYMENT.md) 与 [Docker Compose](DOCKER.md) 中选择一种方式。
3. 按所选指南配置 SSH、持久化数据、备份和带认证的 HTTPS 入口。
4. 上线前逐项完成对应文档中的安全清单和健康检查。

## 文档边界

- `README.md` 是产品入口，不复制完整字段和运维步骤。
- `CONFIGURATION.md` 是配置字段的事实来源。
- `ARCHITECTURE.md` 解释当前代码的行为和有意设计，不承诺路线图。
- `DEPLOYMENT.md` 保留 Python + systemd 的生产步骤。
- `DOCKER.md` 保留 Docker Compose 的构建、运行和维护步骤。
- `DEMO.md` 只处理虚构数据；真实数据库不应进入静态导出流程。

发现文档与代码不一致时，以当前代码和示例配置为准，并欢迎提交带复现步骤的 issue 或补丁。
